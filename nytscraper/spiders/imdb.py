import scrapy
import unidecode
import re
import uuid
from decouple import config
from elasticsearch import Elasticsearch

ELASTIC_API_URL_HOST = config('ELASTIC_API_URL_HOST')
ELASTIC_API_URL_PORT = config('ELASTIC_API_URL_PORT')
ELASTIC_API_USERNAME = config('ELASTIC_API_USERNAME')
ELASTIC_API_PASSWORD = config('ELASTIC_API_PASSWORD')

es=Elasticsearch(host=ELASTIC_API_URL_HOST,
                 scheme='https',
                 port=ELASTIC_API_URL_PORT,
                 http_auth=(ELASTIC_API_USERNAME,ELASTIC_API_PASSWORD))

cleanString = lambda x: '' if x is None else unidecode.unidecode(re.sub(r'\s+', ' ', x))


class imdb(scrapy.Spider):
    name = 'imdb'
    movies = set()
    actors = set()

    def start_requests(self):
        allowed_domains = ['www.imdb.com']
        start_url = 'https://www.imdb.com/title/tt0088763/fullcredits/'
        yield scrapy.Request(url=start_url, callback=self.parse)

    def parse(self, response):
        movie_id = response.url.split("/")[-3]
        if movie_id in self.movies:
            return
        else:
            self.movies.add(movie_id)

        parent = response.css("div.parent").css('h3')
        title = parent.css('a::text').get()
        title = cleanString(title).strip()
        year = parent.css("span::text").get().strip()
        year = re.sub('[()]', '', year)

        cast_list = response.css('table.cast_list')
        new_actors = set()
        for tr in cast_list.css('tr'):
            name = tr.css('td').css('a::text').get()
            name = cleanString(name).strip()
            if name:
                actor_id = tr.css('td').css('a[href]').get()
                actor_id = actor_id.split('/')[2]
                role = tr.css('td.character').css('a::text').get()
                role = cleanString(role).strip()
                if not role:
                    role = tr.css('td.character::text').get()
                    role = cleanString(role).strip()

                try:
                    birthyear = response.meta['birthYear']
                except:
                    birthyear = ''

                yield {
                    "movie_id": movie_id,
                    "movie_name": title,
                    "movie_year": year,
                    "actor_name": name,
                    "actor_id": actor_id,
                    "actor_year": birthyear,
                    "role_name": role
                }

                es.index(index='imdb',
                         doc_type='movies',
                         id=uuid.uuid4(),
                         body={
                             "movie_id": movie_id,
                             "movie_name": title,
                             "movie_year": year,
                             "actor_name": name,
                             "actor_id": actor_id,
                             "actor_year": birthyear,
                             "role_name": role
                         })

                if actor_id in self.actors:
                    continue
                else:
                    self.actors.add(actor_id)
                    new_actors.add(actor_id)

        for actor in new_actors:
            yield response.follow('https://www.imdb.com/name/' + actor, self.parse_actor)

    def parse_actor(self, response):
        entries = response.css('div.filmo-category-section').css('div')
        birthyear = str(response.css('time').xpath('@datetime').get()).split('-')[0]

        for movie in entries:
            try:
                year = movie.css('span.year_column::text').get()
                year = int(year.strip())
            except:
                continue

            if 1980 <= year < 1990:
                movie_id = movie.css('b').css('a[href]').get().split('/')[2]
                type = movie.css('::text')
                if not "TV" in str(type):  # to remove TV Series and TV Movies from our dataset
                    if movie_id:
                        yield response.follow('http://www.imdb.com/title/' + movie_id + '/fullcredits/', self.parse, meta={'birthYear':birthyear})
