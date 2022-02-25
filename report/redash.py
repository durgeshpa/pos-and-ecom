import requests, time
from global_config.views import get_config

class Redash:
    
    REDASH_URL = get_config("redash_url", "https://redash.gramfactory.com/")
    TIMEOUT = get_config("redash_timeout", 10)
    TOKEN = get_config("redash_token", "YJsJ38matoYjdnkPLnHdVa2fDKlc3irfEG1eH0bZ")
    
    def __init__(self, query_no, rid, token=None,) -> None:
        self.query_no = query_no
        self.token = token
        self.result_id = None
        self.rid = rid
    
    def _check_job(self, s, job):
        while job['status'] not in (3,4,5):
            response = s.get('{}/api/jobs/{}'.format(Redash.REDASH_URL, job['id']))
            job = response.json()['job']
            time.sleep(1)

        if job['status'] == 3:
            return job['query_result_id']
        
        if job['status'] == 4:
            raise Exception(job['error'])
        return None
          
    def refresh_query(self, payload):
        with requests.Session() as s:
            s.headers.update({'Authorization': 'Key {}'.format(Redash.TOKEN)})
            response = s.post("{}api/queries/{}/results".format(Redash.REDASH_URL, self.query_no),\
                json=payload)
            if response.status_code != 200:
                raise Exception(response.json()['job']['error'])
            self.result_id = self._check_job(s, response.json()['job'])
            return self._get_results(s)
                
    def _get_results(self, s):
        if self.result_id:
           response = s.get('{}/api/query_results/{}.csv'.format(Redash.REDASH_URL, self.result_id))
           if response.status_code != 200:
               raise Exception("Failure :: Cannot fetch query result")
        else:
            raise Exception("Warning :: No result id present to fetch result, please retry again.")
        
        return response