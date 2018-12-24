import os
import logging

from ckan import model
from ckan.common import g, _, response
from ckan.lib import base
from ckan.logic import NotFound
from ckan.plugins import toolkit
from ckan.views.user import _extra_template_variables

from ckanext.ed.helpers import get_storage_path_for, get_pending_datasets, is_admin, workflow_activity_create
from ckanext.ed.mailer import mail_package_publish_update_to_user, mail_package_publish_request_to_admins


class WorkflowActivityStreamController(base.BaseController):
    def list_activities(self, id):
        '''Render package's workflow activity stream page.'''

        context = {
            'model': model, 'session': model.Session, 'user': toolkit.c.user,
            'for_view': True,'auth_user_obj': toolkit.c.userobj
        }
        data_dict = {'id': id}
        try:
            toolkit.check_access('package_update', context, data_dict)
            toolkit.c.pkg_dict = toolkit.get_action('package_show')(context, data_dict)
            toolkit.c.pkg = context['package']
            toolkit.c.package_activity_stream = toolkit.get_action(
                'package_activity_list_html')(
                context, {
                    'id': toolkit.c.pkg_dict['id'],
                    'get_workflow_activities': True
                })
            dataset_type = toolkit.c.pkg_dict['type'] or 'dataset'
        except NotFound:
            base.abort(404, _('Dataset not found'))
        except toolkit.NotAuthorized:
            base.abort(403, _('Unauthorized to read dataset %s') % id)

        return base.render('package/activity.html', {'dataset_type': dataset_type})


class PendingRequestsController(base.BaseController):
    def list_requests(self):
        if not toolkit.c.userobj:
            base.abort(403, _('Not authorized to see this page'))
        is_editor = not is_admin(toolkit.c.user)
        pending_dataset = get_pending_datasets(toolkit.c.userobj.id, is_editor)
        context = {
            u'for_view': True, u'user': g.user, u'auth_user_obj': g.userobj}
        data_dict = {u'user_obj': g.userobj, u'include_datasets': True}
        extra_vars = _extra_template_variables(context, data_dict)
        extra_vars['pending_dataset'] = pending_dataset
        return base.render(u'user/dashboard_requests.html', extra_vars)


class DownloadController(base.BaseController):
    def download_zip(self, zip_id):
        if not zip_id:
            toolkit.abort(404, toolkit._('Resource data not found'))
        file_name, package_name = zip_id.split('::')
        file_path = get_storage_path_for('temp-ed/' + file_name)

        if not os.path.isfile(file_path):
            toolkit.abort(404, toolkit._('Resource data not found'))

        if not package_name:
            package_name = 'resources'
        package_name += '.zip'

        with open(file_path, 'r') as f:
            response.write(f.read())

        response.headers['Content-Type'] = 'application/octet-stream'
        response.content_disposition = 'attachment; filename=' + package_name
        os.remove(file_path)


class StateUpdateController(base.BaseController):
    def approve(self, id):
        make_public = toolkit.request.params.get(
            'make_public') == 'true'

        _make_action(id, 'approve', make_public=make_public)

    def reject(self, id):
        feedback = toolkit.request.params.get(
            'feedback', 'No feedback provided')
        _make_action(id, 'reject', feedback=feedback)

    def resubmit(self, id):
        _make_action(id, 'resubmit')


def _raise_not_authz(id, action='reject'):
    if action == 'resubmit':
        toolkit.check_access(
            'package_update', {
                'model': model, 'user': toolkit.c.user}, {'id': id})
    else:
        # Check user is admin of the org pakcage is created for
        try:
            package_dict = toolkit.get_action('package_show')(
                {'model': model, 'user': toolkit.c.user}, {'id': id}
            )
        except toolkit.ObjectNotFound:
            # We don't need ObjectNotFound here
            raise toolkit.NotAuthorized

        is_admin_ = is_admin(toolkit.c.user, package_dict['owner_org'])
        if not is_admin_:
            raise toolkit.NotAuthorized


def _make_action(package_id, action='reject', feedback=None, make_public=None):
    action_props = {
        'reject': {
            'state': 'rejected',
            'message': 'Dataset "{0}" rejected',
            'event': 'rejection',
            'mail_func': mail_package_publish_update_to_user,
            'flash_func': toolkit.h.flash_error,
            'activity': 'dataset_rejected'
        },
        'approve': {
            'state': 'approved',
            'message': ('Dataset "{0}" approved and made public'
                        if make_public else 'Dataset "{0}" approved'),
            'event': 'approval',
            'mail_func': mail_package_publish_update_to_user,
            'flash_func': toolkit.h.flash_success,
            'activity': 'dataset_approved'
        },
        'resubmit': {
            'state': 'approval_pending',
            'message': 'Dataset "{0}" submitted',
            'event': 'request',
            'mail_func': mail_package_publish_request_to_admins,
            'flash_func': toolkit.h.flash_success,
            'activity': 'resubmitted_for_review'
        }
    }
    # check access and state
    _raise_not_authz(package_id, action=action)
    context = {'model': model, 'user': toolkit.c.user}
    patch_data = {
        'id': package_id, 'approval_state': action_props[action]['state']
    }
    if make_public:
        patch_data['private'] = False
    data_dict = toolkit.get_action('package_patch')(context, patch_data)
    action_props[action]['mail_func'](
        context,
        data_dict,
        event=action_props[action]['event'],
        feedback=feedback
    )
    action_props[action]['flash_func'](
        action_props[action]['message'].format(data_dict['title']))
    workflow_activity_create(
        activity=action_props[action]['activity'],
        dataset_id=data_dict['id'],
        dataset_name=data_dict['name'],
        user=toolkit.c.user,
        feedback=feedback
    )
    toolkit.redirect_to(
        controller='package', action='read', id=data_dict['name'])
