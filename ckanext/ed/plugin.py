from ckan.lib.activity_streams import activity_stream_string_functions
from ckan.lib.plugins import DefaultTranslation
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.ed import actions, helpers, validators


class EDPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IPackageController, inherit=True)

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'ed_get_groups': helpers.get_groups,
            'ed_is_admin': helpers.is_admin,
            'ed_get_recently_updated_datasets': helpers.get_recently_updated_datasets,
            'ed_get_most_popular_datasets': helpers.get_most_popular_datasets,
            'ed_get_total_views_for_dataset': helpers.get_total_views_for_dataset,
            'ed_get_pending_datasets': helpers.get_pending_datasets,
            'ed_get_latest_rejection_feedback': helpers.get_latest_rejection_feedback,
        }

    # IActions
    def get_actions(self):
        return {
            'ed_prepare_zip_resources': actions.prepare_zip_resources,
            'package_create': actions.package_create,
            'package_show': actions.package_show,
            'package_activity_list': actions.package_activity_list,
            'dashboard_activity_list': actions.dashboard_activity_list,
            'group_activity_list': actions.group_activity_list,
            'recently_changed_packages_activity_list': actions.recently_changed_packages_activity_list
        }

    # IPackageController
    def before_search(self, search_params):
        # For requests dashboard we need approval_pending datasets. Passing in
        # extras that request is sent from dashboard. Return params as is if so
        if search_params.get('extras', {}).get('from_dashboard'):
            return search_params

        search_params.update({
            'fq': '!(approval_state:approval_pending OR approval_state:rejected) ' + search_params.get('fq', '')
        })
        return search_params

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ed')

        activity_stream_string_functions['changed package'] = helpers.custom_activity_renderer


    # IRoutes
    def before_map(self, map):
        publish_controller = 'ckanext.ed.controller:StateUpdateController'
        map.connect('dataset.workflow', '/dataset/workflow/{id}',
                    controller='ckanext.ed.controller:WorkflowActivityStreamController',
                    action='list_activities')
        map.connect('dashboard.requests', '/dashboard/requests',
                    controller='ckanext.ed.controller:PendingRequestsController',
                    action='list_requests')
        map.connect('/dataset-publish/{id}/approve',
                    controller=publish_controller,
                    action='approve')
        map.connect('/dataset-publish/{id}/reject',
                    controller=publish_controller,
                    action='reject')
        map.connect('/dataset-publish/{id}/resubmit',
                    controller=publish_controller,
                    action='resubmit')
        map.connect(
            'download_zip',
            '/download/zip/{zip_id}',
            controller='ckanext.ed.controller:DownloadController',
            action='download_zip'
        )

        return map

    # IValidators
    def get_validators(self):
        return {
            'state_validator': validators.state_validator
        }
