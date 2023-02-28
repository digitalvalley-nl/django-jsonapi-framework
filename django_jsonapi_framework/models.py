from django.db.models import CharField


class JSONAPISerializable:

    def jsonapi_post_save(self):
        pass

    def jsonapi_pre_save(self):
        pass

    def _jsonapi_from_data(self, data):
        for attribute in self.JSONAPIMeta.write_attributes:
            if attribute in data['attributes']:
                setattr(self, attribute, data['attributes'][attribute])

    def _jsonapi_to_data(self):
        data = {
            'id': self.id,
            'type': self.__class__.__name__,
            'attributes': {},
            'relationships': {}
        }
        for attribute in self.JSONAPIMeta.read_attributes:
            data['attributes'][attribute] = getattr(self, attribute)
        if len(data['attributes'].keys()) == 0:
            del data['attributes']
        if len(data['relationships'].keys()) == 0:
            del data['relationships']
        return data

    class JSONAPIMeta:
        read_attributes = []
        write_attributes = []
