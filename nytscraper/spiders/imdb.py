import scrapy
import unidecode
import re

cleanString = lambda x: '' if x is None else unidecode.unidecode(re.sub(r'\s+',' ',x))

class imdb(scrapy.Spider):
    name = 'imdb'

    def start_requests(self):
        allowed_domains = ['www.imdb.com']
        start_url = 'https://www.imdb.com/title/tt0088763/fullcredits/'
        yield scrapy.Request(url=start_url, callback=self.parse)

    def parse(self, response):
        movieId = response.url.split("/")[-3]
        parent = response.css("div.parent").css('h3')
        title = parent.css('a::text').get()
        title = cleanString(title).strip()
        year = parent.css("span::text").get().strip()
        year = re.sub('[()]', '', year)

        cast_list = response.css('table.cast_list')
        for tr in cast_list.css('tr'):
            name = tr.css('td').css('a::text').get()
            name = cleanString(name).strip()
            if(name):
                actor_id = tr.css('td').css('a[href]').get()
                actor_id = actor_id.split('/')[2]
                role = tr.css('td.character').css('a::text').get()
                if (not role):
                    role = tr.css('td.character::text').get()
                    role = cleanString(role).strip()
                    
                yield {
                    "movie_id": movieId,
                    "movie_name": title,
                    "movie_year": year,
                    "actor_name": name,
                    "actor_id": actor_id,
                    "role_name": role
                }
