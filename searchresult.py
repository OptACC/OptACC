from collections import namedtuple

'''Represents the results of searching for an optimal point'''
SearchResult = namedtuple('SearchResult',
        ['optimal', 'tests', 'num_iterations'])
