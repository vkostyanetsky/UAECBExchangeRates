import datetime

from pymongo import MongoClient
from pymongo import collection as collection


class CrawlerDB:

    DB: object = None
    RATES: collection = None
    DATE_FORMAT_STRING: str = "%Y%m%d"
    DATETIME_FORMAT_STRING: str = "%Y%m%d%H%M%S"

    def __init__(self, config: dict):

        client = MongoClient(config['mongodb_connection_string'], serverSelectionTimeoutMS=config['mongodb_max_delay'])

        CrawlerDB.DB = client[config['mongodb_database_name']]
        CrawlerDB.RATES = CrawlerDB.DB['currency_rates']

    @classmethod
    def get_currency_rates(cls, currency_code: str, date: datetime.datetime = None):

        def get_stage_1():

            stage = {
                '$match':
                    {
                        'currency_code': {'$eq': currency_code.upper()}
                    }
            }

            if date is not None:
                stage['$match']['written_at'] = {'$gt': date}

            return stage

        def get_stage_2():

            return {
                '$group':
                    {
                        '_id': '$valid_from',
                        'written_at':
                            {
                                '$max':
                                    {
                                        'written_at':       '$written_at',
                                        'currency_rate':    '$currency_rate'
                                    }
                            },
                    }
            }

        def get_stage_3():

            return {
                '$sort':
                    {
                        '_id': 1
                    }
            }

        stage_1 = get_stage_1()
        stage_2 = get_stage_2()
        stage_3 = get_stage_3()

        stages = [stage_1, stage_2, stage_3]
        cursor = cls.RATES.aggregate(stages)

        rates = []

        for rate in cursor:

            rates.append({
                'written_at':       rate['written_at']['written_at'].strftime(CrawlerDB.DATETIME_FORMAT_STRING),
                'valid_from':       rate['_id'].strftime(CrawlerDB.DATE_FORMAT_STRING),
                'currency_rate':    rate['written_at']['currency_rate']
            })

        return rates

    @classmethod
    def add_currency_rates(cls, rates):
        cls.RATES.insert_many(rates)

    @classmethod
    def write_new_currency_rate(cls, rate):

        query = {
            '$and': [
                {'currency_code': {'$eq': rate['currency_code']}},
                {'currency_rate': {'$eq': rate['currency_rate']}},
                {'valid_from':    {'$eq': rate['valid_from']}},
            ]}

        if cls.RATES.count_documents(query) == 0:
            cls.RATES.insert_one(rate)

    @classmethod
    def check_for_ambiguous_currency_rate(cls, rate):

        query = {
            '$and': [
                {'currency_code': {'$eq': rate['currency_code']}},
                {'currency_rate': {'$ne': rate['currency_rate']}},
                {'valid_from':    {'$eq': rate['valid_from']}},
            ]}

        if cls.RATES.count_documents(query) > 0:
            # TODO Telegram alert required
            print('?')

