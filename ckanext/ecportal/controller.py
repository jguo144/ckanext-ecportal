from ckan.lib.base import c, model
from ckan.lib.field_types import DateType, DateConvertError
from ckan.authz import Authorizer
from ckan.lib.navl.dictization_functions import Invalid
from fields import GeoCoverageType
from ckan.lib.navl.dictization_functions import missing
from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,
                                     )
import ckan.logic.validators as val
import ckan.logic.schema as default_schema
from ckan.controllers.package import PackageController

import logging
log = logging.getLogger(__name__)

geographic_granularity = [('', ''),
                          ('national', 'national'),
                          ('regional', 'regional'),
                          ('local authority', 'local authority'),
                          ('ward', 'ward'),
                          ('point', 'point'),
                          ('other', 'other - please specify')]

update_frequency = [('', ''),
                    ('never', 'never'),
                    ('discontinued', 'discontinued'),
                    ('annual', 'annual'),
                    ('quarterly', 'quarterly'),
                    ('monthly', 'monthly'),
                    ('other', 'other - please specify')]

temporal_granularity = [("",""),
                       ("year","year"),
                       ("quarter","quarter"),
                       ("month","month"),
                       ("week","week"),
                       ("day","day"),
                       ("hour","hour"),
                       ("point","point"),
                       ("other","other - please specify")]


class ECPortalController(PackageController):
    package_form = 'package_ecportal.html'

    def _setup_template_variables(self, context, data_dict=None):
        c.licences = [('', '')] + model.Package.get_license_options()
        c.geographic_granularity = geographic_granularity
        c.update_frequency = update_frequency
        c.temporal_granularity = temporal_granularity 

        c.publishers = self.get_publishers()

        c.is_sysadmin = Authorizer().is_sysadmin(c.user)
        c.resource_columns = model.Resource.get_columns()

        # This is messy as auths take domain object not data_dict
        pkg = context.get('package') or c.pkg
        if pkg:
            c.auth_for_change_state = Authorizer().am_authorized(
                c, model.Action.CHANGE_STATE, pkg)

    def _form_to_db_schema(self):
        schema = {
            'title': [not_empty, unicode],
            'name': [not_empty, unicode, val.name_validator, val.package_name_validator],
            'notes': [not_empty, unicode],

            'date_released': [date_to_db, convert_to_extras],
            'date_updated': [date_to_db, convert_to_extras],
            'date_update_future': [date_to_db, convert_to_extras],
            'update_frequency': [use_other, unicode, convert_to_extras],
            'update_frequency-other': [],
            'precision': [unicode, convert_to_extras],
            'geographic_granularity': [use_other, unicode, convert_to_extras],
            'geographic_granularity-other': [],
            'geographic_coverage': [ignore_missing, convert_geographic_to_db, convert_to_extras],
            'temporal_granularity': [use_other, unicode, convert_to_extras],
            'temporal_granularity-other': [],
            'temporal_coverage-from': [date_to_db, convert_to_extras],
            'temporal_coverage-to': [date_to_db, convert_to_extras],
            'url': [unicode],
            'taxonomy_url': [unicode, convert_to_extras],

            'resources': default_schema.default_resource_schema(),
            
            'published_by': [not_empty, unicode, convert_to_extras],
            'published_via': [ignore_missing, unicode, convert_to_extras],
            'author': [ignore_missing, unicode],
            'author_email': [ignore_missing, unicode],
            'mandate': [ignore_missing, unicode, convert_to_extras],
            'license_id': [ignore_missing, unicode],
            'tag_string': [ignore_missing, val.tag_string_convert],
            'national_statistic': [ignore_missing, convert_to_extras],
            'state': [val.ignore_not_admin, ignore_missing],

            'log_message': [unicode, val.no_http],

            '__extras': [ignore],
            '__junk': [empty],
        }
        return schema
    
    def _db_to_form_schema(data):
        schema = {
            'date_released': [convert_from_extras, ignore_missing, date_to_form],
            'date_updated': [convert_from_extras, ignore_missing, date_to_form],
            'date_update_future': [convert_from_extras, ignore_missing, date_to_form],
            'update_frequency': [convert_from_extras, ignore_missing, extract_other(update_frequency)],
            'precision': [convert_from_extras, ignore_missing],
            'geographic_granularity': [convert_from_extras, ignore_missing, extract_other(geographic_granularity)],
            'geographic_coverage': [convert_from_extras, ignore_missing, convert_geographic_to_form],
            'temporal_granularity': [convert_from_extras, ignore_missing, extract_other(temporal_granularity)],
            'temporal_coverage-from': [convert_from_extras, ignore_missing, date_to_form],
            'temporal_coverage-to': [convert_from_extras, ignore_missing, date_to_form],
            'taxonomy_url': [convert_from_extras, ignore_missing],

            'resources': default_schema.default_resource_schema(),
            'extras': {
                'key': [],
                'value': [],
                '__extras': [keep_extras]
            },
            'tags': {
                '__extras': [keep_extras]
            },
            
            'published_by': [convert_from_extras, ignore_missing],
            'published_via': [convert_from_extras, ignore_missing],
            'mandate': [convert_from_extras, ignore_missing],
            'national_statistic': [convert_from_extras, ignore_missing],
            '__extras': [keep_extras],
            '__junk': [ignore],
        }
        return schema

    def _check_data_dict(self, data_dict):
        return

    def get_publishers(self):
        return [('pub1', 'pub2')]

def date_to_db(value, context):
    try:
        value = DateType.form_to_db(value)
    except DateConvertError, e:
        raise Invalid(str(e))
    return value

def date_to_form(value, context):
    try:
        value = DateType.db_to_form(value)
    except DateConvertError, e:
        raise Invalid(str(e))
    return value

def convert_to_extras(key, data, errors, context):

    extras = data.get(('extras',), [])
    if not extras:
        data[('extras',)] = extras

    extras.append({'key': key[-1], 'value': data[key]})

def convert_from_extras(key, data, errors, context):

    for data_key, data_value in data.iteritems():
        if (data_key[0] == 'extras' 
            and data_key[-1] == 'key'
            and data_value == key[-1]):
            data[key] = data[('extras', data_key[1], 'value')]

def use_other(key, data, errors, context):

    other_key = key[-1] + '-other'
    other_value = data.get((other_key,), '').strip()
    if other_value:
        data[key] = other_value

def extract_other(option_list):

    def other(key, data, errors, context):
        value = data[key]
        if value in dict(option_list).keys():
            return
        elif value is missing:
            data[key] = ''
            return
        else:
            data[key] = 'other'
            other_key = key[-1] + '-other'
            data[(other_key,)] = value
    return other
            
def convert_geographic_to_db(value, context):

    if isinstance(value, list):
        regions = value
    elif value:
        regions = [value]
    else:
        regions = []
        
    return GeoCoverageType.get_instance().form_to_db(regions)

def convert_geographic_to_form(value, context):

    return GeoCoverageType.get_instance().db_to_form(value)

