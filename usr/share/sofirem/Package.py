'''
    This class is to encapsulate package metadata.
    It is is used inside the following:
    - Functions.userSearch()
'''
class Package(object):
    def __init__(self, name, description, category, category_description):
        self.name = name
        self.description = description
        self.category = category
        self.category_description = category_description
