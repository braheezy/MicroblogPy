'''
All search functionality is in this module, promoting the abstract search
design we want. Should we need to swap out the underlying search logic
away from Elasticsearch, we can focus on editing this file.
'''
from flask import current_app


# Add new entries to the full-text index.
# Can also be used to modify existing objects.
def add_to_index(index, model):
    if not current_app.elasticsearch:
        return
    payload = {}
    # Gather fields from searchable attribute.
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    # Conveintely use the id assigned by SQLAlchemy
    current_app.elasticsearch.index(index=index, id=model.id, body=payload)


# Remove entries to the full-text index.
def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, id=mode.id)


def query_index(index, query, page, per_page):
    if not current_app.elasticsearch:
        return [], 0
    # This search looks at multiple fields, and by using '*', doesn't
    # care what the field names are. This also has pagination options.
    search = current_app.elasticsearch.search(index=index,
                                              body={
                                                  'query': {
                                                      'multi_match': {
                                                          'query': query,
                                                          'fields': ['*']
                                                      }
                                                  },
                                                  'from':
                                                  (page - 1) * per_page,
                                                  'size': per_page
                                              })
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    # Return a list of id elements from results and total number of results.
    return ids, search['hits']['total']['value']