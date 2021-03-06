import json
import ckan.model as model
import ckan.plugins as plugins
import ckan.logic as logic
import ckan.lib.helpers as h
import ckan.lib.create_test_data
import ckan.tests as tests

_create_test_data = ckan.lib.create_test_data.CreateTestData


def create_vocab(vocab_name, user_name):
    context = {'model': model, 'session': model.Session,
               'user': user_name}
    vocab = logic.get_action('vocabulary_create')(
        context, {'name': vocab_name}
    )
    return vocab


def add_tag_to_vocab(tag_name, vocab_id, user_name):
    tag_schema = logic.schema.default_create_tag_schema()
    tag_schema['name'] = [unicode]
    context = {'model': model, 'session': model.Session,
               'user': user_name, 'schema': tag_schema}
    tag = {'name': tag_name,
           'vocabulary_id': vocab_id}
    logic.get_action('tag_create')(context, tag)


class TestAPI(tests.WsgiAppCase):
    @classmethod
    def setup_class(cls):
        _create_test_data.create('publisher')
        model.repo.new_revision()

        usr = model.User(name="ectest", apikey="ectest", password=u'ectest')
        model.Session.add(usr)
        model.Session.commit()

        g = model.Group.get('david')
        g.type = 'organization'
        model.Session.add(g)

        p = model.Package.get('warandpeace')
        mu = model.Member(table_id=usr.id, table_name='user', group=g)
        mp = model.Member(table_id=p.id, table_name='package', group=g)
        model.Session.add(mu)
        model.Session.add(mp)
        model.Session.commit()

        cls.sysadmin_user = model.User.get('testsysadmin')

        status = create_vocab(u'status', cls.sysadmin_user.name)
        add_tag_to_vocab(u'http://purl.org/adms/status/Completed',
                         status['id'], cls.sysadmin_user.name)

        plugins.load('ecportal')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        plugins.unload('ecportal')

    def test_package_rdf_create_ns_update(self):
        rdf = ('<rdf:RDF '
               'xmlns:foaf="http://xmlns.com/foaf/0.1/" '
               'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
               'xmlns:dct="http://purl.org/dc/terms/" '
               'xmlns:dcat="http://www.w3.org/ns/dcat#"> '
               '<dcat:Dataset rdf:about="http://localhost"></dcat:Dataset> '
               '</rdf:RDF>')
        dataset_json = json.dumps({
            'name': u'rdfpackage2',
            'title': u'RDF Package2',
            'description': u'RDF package 2 description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'rdf': rdf
        })
        response = self.app.post('/api/action/package_create',
                                 params=dataset_json,
                                 extra_environ={'Authorization': 'ectest'})
        dataset = json.loads(response.body)['result']
        assert 'dcat=' in dataset['rdf']

        # Fetch RDF page
        response = self.app.get(h.url_for(
            controller='package', action='read', id='rdfpackage2'
        ) + ".rdf")
        assert '/dataset/rdfpackage2' in response.body, response.body

    def test_package_rdf_create_ns_new(self):
        rdf = ('<rdf:RDF '
               'xmlns:foaf="http://xmlns.com/foaf/0.1/" '
               'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
               'xmlns:dcat="http://www.w3.org/ns/dcat#"> '
               '<dcat:Dataset rdf:about="http://localhost"></dcat:Dataset> '
               '</rdf:RDF>')
        dataset_json = json.dumps({
            'name': u'rdfpackage1',
            'title': u'RDF Package1',
            'description': u'RDF package 2 description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'rdf': rdf
        })
        response = self.app.post('/api/action/package_create',
                                 params=dataset_json,
                                 extra_environ={'Authorization': 'ectest'})
        dataset = json.loads(response.body)['result']
        assert 'dcat=' in dataset['rdf']

        # Fetch RDF page
        response = self.app.get(h.url_for(
            controller='package', action='read', id='rdfpackage1'
        ) + ".rdf")
        assert '/dataset/rdfpackage1' in response.body, response.body

    def test_keywords_create(self):
        tag = u'test-keyword'
        dataset_json = json.dumps({
            'name': u'test_keywords_dataset',
            'title': u'Test Keywords Dataset',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'keywords': [{u'name': tag}]
        })
        response = self.app.post('/api/action/package_create',
                                 params=dataset_json,
                                 extra_environ={'Authorization': 'ectest'})
        dataset = json.loads(response.body)['result']

        tags = [t['name'] for t in dataset['keywords']]
        assert len(tags) == 1
        assert tag in tags

    def test_keywords_update(self):
        params = json.dumps({'id': u'warandpeace'})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']
        old_tags = dataset.pop('keywords')
        new_tag_names = [u'test-keyword1', u'test-keyword2']
        new_tags = old_tags + [{'name': name} for name in new_tag_names]
        dataset['keywords'] = new_tags
        dataset['description'] = u'test description'
        dataset['url'] = u'http://datahub.io'
        dataset['status'] = u'http://purl.org/adms/status/Completed'

        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': 'ectest'})
        updated_dataset = json.loads(response.body)['result']

        old_tags = [tag['name'] for tag in old_tags]
        updated_tags = [tag['name'] for tag in updated_dataset['keywords']]

        for tag in old_tags:
            assert tag in updated_tags
        for tag in new_tag_names:
            assert tag in updated_tags

    def test_convert_publisher_to_groups(self):
        params = json.dumps({'id': u'warandpeace'})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']
        assert dataset['published_by'] == u'david'

        dataset['description'] = u'test description'
        dataset['url'] = u'http://datahub.io'
        dataset['status'] = u'http://purl.org/adms/status/Completed'
        dataset['published_by'] = u'roger'
        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': 'ectest'})
        updated_dataset = json.loads(response.body)['result']
        assert updated_dataset['published_by'] == u'david', updated_dataset

    def test_uppercase_names_allowed(self):
        dataset_json = json.dumps({
            'name': u'TEST-UPPERCASE-NAMES',
            'title': u'Test',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
        })
        self.app.post('/api/action/package_create',
                      params=dataset_json,
                      extra_environ={'Authorization': 'ectest'})

    def test_contact_name_required(self):
        dataset_json = json.dumps({
            'name': u'TEST-UPPERCASE-NAMES',
            'title': u'Test',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'contact_email': u'contact@email.com',
        })
        self.app.post('/api/action/package_create',
                      params=dataset_json,
                      extra_environ={'Authorization': 'ectest'},
                      status=409)

    def test_blank_license_allowed(self):
        dataset_json = json.dumps({
            'name': u'test-blank-license-string',
            'title': u'Test',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'contact_email': u'contact@email.com',
            'license_id': u''
        })
        self.app.post('/api/action/package_create',
                      params=dataset_json,
                      extra_environ={'Authorization': 'ectest'},
                      status=409)

        dataset_json = json.dumps({
            'name': u'test-blank-license-list',
            'title': u'Test',
            'description': u'test description',
            'url': u'http://datahub.io',
            'published_by': u'david',
            'status': u'http://purl.org/adms/status/Completed',
            'contact_email': u'contact@email.com',
            'license_id': []
        })
        self.app.post('/api/action/package_create',
                      params=dataset_json,
                      extra_environ={'Authorization': 'ectest'},
                      status=409)

    def test_purge_publisher_datasets(self):
        dataset = {'name': u'test-purge-publisher-datasets',
                   'title': u'Test',
                   'description': u'test description',
                   'url': u'http://datahub.io',
                   'published_by': u'david',
                   'status': u'http://purl.org/adms/status/Completed'}
        env = {'Authorization': 'ectest'}
        self.app.post('/api/action/package_create',
                      params=json.dumps(dataset),
                      extra_environ=env)

        params = {'id': dataset['name']}
        self.app.post('/api/action/package_delete',
                      params=json.dumps(params),
                      extra_environ=env)

        params = {'name': dataset['published_by']}
        env = {'Authorization': str(self.sysadmin_user.apikey)}
        response = self.app.post('/api/action/purge_publisher_datasets',
                                 params=json.dumps(params),
                                 extra_environ=env)

        result = json.loads(response.body)['result']
        assert result['publisher_datasets_deleted'] == 1

    def test_purge_publisher_datasets_invalid_auth(self):
        dataset = {'name': u'test-purge-publisher-datasets-invalid-auth',
                   'title': u'Test',
                   'description': u'test description',
                   'url': u'http://datahub.io',
                   'published_by': u'david',
                   'status': u'http://purl.org/adms/status/Completed'}
        env = {'Authorization': 'ectest'}
        self.app.post('/api/action/package_create',
                      params=json.dumps(dataset),
                      extra_environ=env)

        params = {'id': dataset['name']}
        self.app.post('/api/action/package_delete',
                      params=json.dumps(params),
                      extra_environ=env)

        # test no api key
        params = {'name': dataset['published_by']}
        self.app.post('/api/action/purge_publisher_datasets',
                      params=json.dumps(params),
                      status=403)

        # test non-sysadmin api key
        self.app.post('/api/action/purge_publisher_datasets',
                      params=json.dumps(params),
                      extra_environ=env,
                      status=403)

    def test_purge_publisher_datasets_invalid_publisher(self):
        dataset = {'name': u'test-purge-publisher-datasets-invalid-publisher',
                   'title': u'Test',
                   'description': u'test description',
                   'url': u'http://datahub.io',
                   'published_by': u'david',
                   'status': u'http://purl.org/adms/status/Completed'}
        env = {'Authorization': 'ectest'}
        self.app.post('/api/action/package_create',
                      params=json.dumps(dataset),
                      extra_environ=env)

        params = {'id': dataset['name']}
        self.app.post('/api/action/package_delete',
                      params=json.dumps(params),
                      extra_environ=env)

        params = {'name': 'bad-publisher-name'}
        env = {'Authorization': str(self.sysadmin_user.apikey)}

        self.app.post('/api/action/purge_publisher_datasets',
                      params=json.dumps(params),
                      extra_environ=env,
                      status=404)
