import os
from genshi.input import HTML
from genshi.filters import Transformer
from ckan.plugins import implements, SingletonPlugin, IRoutes, IConfigurable,\
    IConfigurer, IGenshiStreamFilter
import ckanext.ecportal
import html

from logging import getLogger
log = getLogger(__name__)

def configure_template_directory(config, relative_path):
    configure_served_directory(config, relative_path, 'extra_template_paths')

def configure_public_directory(config, relative_path):
    configure_served_directory(config, relative_path, 'extra_public_paths')

def configure_served_directory(config, relative_path, config_var):
    'Configure serving of public/template directories.'
    assert config_var in ('extra_template_paths', 'extra_public_paths')
    this_dir = os.path.dirname(ckanext.ecportal.__file__)
    absolute_path = os.path.join(this_dir, relative_path)
    if absolute_path not in config.get(config_var, ''):
        if config.get(config_var):
            config[config_var] += ',' + absolute_path
        else:
            config[config_var] = absolute_path

class ECPortalPlugin(SingletonPlugin):
    implements(IRoutes)
    implements(IConfigurable)
    implements(IConfigurer)
    implements(IGenshiStreamFilter)

    def before_map(self, map):
        map.connect('/dataset/new', controller='ckanext.ecportal.controller:ECPortalController', action='new')
        map.connect('/dataset/edit/{id}', controller='ckanext.ecportal.controller:ECPortalController', action='edit')
        return map

    def after_map(self, map):
        return map

    def configure(self, config):
        self.site_url = config.get('ckan.site_url')

    def update_config(self, config):
        configure_template_directory(config, 'templates')
        configure_public_directory(config, 'public')

    def filter(self, stream):
        from pylons import request
        routes = request.environ.get('pylons.routes_dict')

        # add javascript file to new dataset form so slug is generated correctly
        if routes and 'ECPortalController' in routes.get('controller') and \
            routes.get('action') == 'new':
                stream = stream | Transformer('body').append(
                    HTML(html.JS % {'site_url': self.site_url})
                )

        return stream


# class FormApiPlugin(SingletonPlugin):
#     """
#     Configures the Form API and harvesting used by Drupal.
#     """

#     implements(IRoutes)
#     implements(IConfigurer)
#     implements(IGenshiStreamFilter)

#     def before_map(self, map):

#         map.connect('/package/new', controller='package_formalchemy', action='new')
#         map.connect('/package/edit/{id}', controller='package_formalchemy', action='edit')

#         for version in ('', '1/'):
#             map.connect('/api/%sform/package/create' % version, controller='ckanext.dgu.forms.formapi:FormController', action='package_create')
#             map.connect('/api/%sform/package/edit/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='package_edit')
#             map.connect('/api/%sform/harvestsource/create' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_create')
#             map.connect('/api/%sform/harvestsource/edit/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_edit')
#             map.connect('/api/%sform/harvestsource/delete/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_delete')
#             map.connect('/api/%srest/harvestsource/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_view')
#         map.connect('/api/2/form/package/create', controller='ckanext.dgu.forms.formapi:Form2Controller', action='package_create')
#         map.connect('/api/2/form/package/edit/:id', controller='ckanext.dgu.forms.formapi:Form2Controller', action='package_edit')
#         map.connect('/api/2/form/harvestsource/create', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_create')
#         map.connect('/api/2/form/harvestsource/edit/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_edit')
#         map.connect('/api/2/form/harvestsource/delete/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_delete')
#         map.connect('/api/2/rest/harvestsource', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_list')
#         map.connect('/api/2/rest/harvestsource/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_view')
#         # I had to add this line!!!!
#         map.connect('/api/2/rest/harvestsource/publisher/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_list')
#         map.connect('/api/2/rest/harvestingjob', controller='ckanext.dgu.forms.formapi:FormController',
#                 action='harvesting_job_create',
#                 conditions=dict(method=['POST']))
#         """
#         These routes are implemented in ckanext-csw
#         map.connect('/api/2/rest/harvesteddocument/:id/xml/:id2.xml', controller='ckanext.dgu.forms.formapi:FormController',
#                 action='harvested_document_view_format',format='xml')
#         map.connect('/api/rest/harvesteddocument/:id/html', controller='ckanext.dgu.forms.formapi:FormController',
#                 action='harvested_document_view_format', format='html')
#         """
#         map.connect('/api/2/util/publisher/:id/department', controller='ckanext.dgu.forms.formapi:FormController', action='get_department_from_organisation')
#         #map.connect('/', controller='ckanext.dgu.controllers.catalogue:CatalogueController', action='home')
#         #map.connect('home', '/ckan/', controller='home', action='index')
#         return map

#     def after_map(self, map):
#         return map

#     def update_config(self, config):
#         #configure_template_directory(config, 'theme_common/templates')
#         #configure_public_directory(config, 'theme_common/public')

#         # set the customised package form (see ``setup.py`` for entry point)
#         config['package_form'] = 'package_gov3'
#         configure_template_directory(config, 'templates')

#     def filter(self, stream):

#         from pylons import request, tmpl_context as c
#         routes = request.environ.get('pylons.routes_dict')

#         if routes and \
#                routes.get('controller') == 'package' and \
#                routes.get('action') == 'read' and c.pkg.id:

#             is_inspire = [v[1] for i,v in enumerate(c.pkg_extras) if v[0] == 'INSPIRE']
#             if is_inspire and is_inspire[0] == 'True':
#                 stream = stream_filters.harvest_filter(stream, c.pkg)

#             # Add dataset id to the UI
#             stream = stream_filters.package_id_filter(stream, c.pkg)
#         return stream
