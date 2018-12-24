import mock

from nose.tools import assert_raises

from ckan.lib.helpers import url_for
from ckan.lib.search import rebuild
from ckan.logic import NotFound
from ckan.plugins import toolkit
from ckan.tests import helpers, factories

class TestPendingRequestsController(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):

        helpers.reset_db()
        super(TestPendingRequestsController, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        super(TestPendingRequestsController, cls).teardown_class()
        helpers.reset_db()

    def setup(self):
        super(TestPendingRequestsController, self).setup()
        sysadmin = factories.Sysadmin()


    def test_requests_tab_not_appears_for_member_on_dashboard(self):
        app = self._get_test_app()
        member = factories.User()
        factories.Organization(users=[{'name': member['name'], 'capacity': 'reader'}])

        extra_environ = {'REMOTE_USER': member['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert '<a href="/dashboard/requests">Requests</a>' not in resp

    def test_requests_tab_appears_for_editor_on_dashboard(self):
        app = self._get_test_app()
        editor = factories.User()
        factories.Organization(users=[{'name': editor['name'], 'capacity': 'editor'}])
        org = factories.Organization(users=[{'name': editor['name'], 'capacity': 'editor'}])
        context = {'user': editor['name']}
        data_dict = _create_dataset_dict('test-pending-1', org['id'])
        helpers.call_action('package_create', context, **data_dict)

        extra_environ = {'REMOTE_USER': editor['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert '<a href="/dashboard/requests">Pending dataset requests (1)</a>' in resp

    def test_requests_tab_not_appears_for_non_creator_editor_on_dashboard(self):
        app = self._get_test_app()
        editor = factories.User()
        editor_2 = factories.User()
        org = factories.Organization(users=[{'name': editor['name'], 'capacity': 'editor'}])
        context = {'user': editor['name']}
        data_dict = _create_dataset_dict('test-pending-1', org['id'])
        helpers.call_action('package_create', context, **data_dict)

        extra_environ = {'REMOTE_USER': editor_2['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert '<a href="/dashboard/requests">Pending dataset requests (0)</a>' in resp

    def test_requests_tab_appears_for_admin_on_dashboard(self):
        app = self._get_test_app()
        editor = factories.User()
        factories.Organization(users=[{'name': editor['name'], 'capacity': 'admin'}])

        extra_environ = {'REMOTE_USER': editor['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert '<a href="/dashboard/requests">Pending dataset requests (0)</a>' in resp, resp

    def test_requests_tab_appears_for_sysadmin_on_dashboard(self):
        app = self._get_test_app()
        sysadmin = factories.Sysadmin()
        factories.Organization(users=[{'name': sysadmin['name'], 'capacity': 'sysadmin'}])

        extra_environ = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert '<a href="/dashboard/requests">Pending dataset requests (0)</a>' in resp

    def test_pending_datasets_show_up_on_dashboard(self):
        app = self._get_test_app()
        # Create Users
        editor = factories.User()
        admin = factories.User()
        factories.Organization(
            users=[
                {'name': admin['name'], 'capacity': 'admin'},
                {'name': editor['name'], 'capacity': 'editor'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        # Create Datasets
        context = {'user': editor['name']}
        data_dict = _create_dataset_dict('test-pending-1', 'us-ed-1')
        helpers.call_action('package_create', context, **data_dict)

        extra_environ = {'REMOTE_USER': admin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert 'TEST-PENDING-1' in resp, resp

    def test_non_pending_datasets_do_not_show_up_on_dashboard(self):
        app = self._get_test_app()
        # Create Users
        editor = factories.User()
        admin = factories.User()
        factories.Organization(
            users=[
                {'name': admin['name'], 'capacity': 'admin'},
                {'name': editor['name'], 'capacity': 'editor'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        # Create Datasets
        context = {'user': admin['name']}
        data_dict_1 = _create_dataset_dict('test-pending-1', 'us-ed-1')
        helpers.call_action('package_create', context, **data_dict_1)
        context = {'user': editor['name']}
        data_dict_2 = _create_dataset_dict('test-pending-2', 'us-ed-1')
        helpers.call_action('package_create', context, **data_dict_2)

        extra_environ = {'REMOTE_USER': admin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        # By admin should not be there
        assert 'TEST-PENDING-1' not in resp
        # By editor should be there
        assert 'TEST-PENDING-2' in resp

    def test_pending_datasets_from_other_office_dont_show_up_for_admin(self):
        app = self._get_test_app()
        # Create Users
        editor_native = factories.User()
        editor_forigner = factories.User()
        admin = factories.User()
        factories.Organization(
            users=[
                {'name': admin['name'], 'capacity': 'admin'},
                {'name': editor_native['name'], 'capacity': 'editor'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        factories.Organization(
            users=[{'name': editor_forigner['name'], 'capacity': 'editor'}],
            name='us-ed-2',
            id='us-ed-2'
        )
        # Create Datasets
        context = {'user': editor_native['name']}
        data_dict_native = _create_dataset_dict('test-pending-native', 'us-ed-1')
        helpers.call_action('package_create', context, **data_dict_native)

        context = {'user': editor_forigner['name']}
        data_dict_forign = _create_dataset_dict('test-pending-forign', 'us-ed-2')
        helpers.call_action('package_create', context, **data_dict_forign)

        extra_environ = {'REMOTE_USER': admin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert 'TEST-PENDING-FORIGN' not in resp
        assert 'TEST-PENDING-NATIVE' in resp


    def test_pending_private_datasets_show_up_on_dashboard(self):
        app = self._get_test_app()
        # Create Users
        editor = factories.User()
        admin = factories.User()
        factories.Organization(
            users=[
                {'name': admin['name'], 'capacity': 'admin'},
                {'name': editor['name'], 'capacity': 'editor'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        # Create Dataset
        context = {'user': editor['name']}
        data_dict = _create_dataset_dict('test-pending-private', 'us-ed-1', private=True)
        helpers.call_action('package_create', context, **data_dict)

        extra_environ = {'REMOTE_USER': admin['name'].encode('ascii')}
        resp = app.get(url=url_for('dashboard.requests'), extra_environ=extra_environ)
        assert 'TEST-PENDING-PRIVATE' in resp, resp


class TestStateUpdateController(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):

        helpers.reset_db()
        super(TestStateUpdateController, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        super(TestStateUpdateController, cls).teardown_class()
        helpers.reset_db()

    def setup(self):
        super(TestStateUpdateController, self).setup()
        self.pkg = 'test-dataset-1'
        helpers.reset_db()
        rebuild()
        factories.User(name='george', id='george')
        factories.User(name='john', id='john')
        factories.User(name='paul', id='paul')
        factories.Organization(
            users=[
                {'name': 'george', 'capacity': 'admin'},
                {'name': 'john', 'capacity': 'editor'},
                {'name': 'paul', 'capacity': 'reader'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        # Dataset created by factories seem to use sysadmin so approval_state
        # forced to be "approved". Creating packages this way to avoid that
        context = {'user': 'john'}
        data_dict = _create_dataset_dict(self.pkg, 'us-ed-1', private=True)
        self.package = helpers.call_action('package_create', context, **data_dict)


    def test_dataset_reject_403_for_anonimous_users(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            app.get(url=url_for('/dataset-publish/{0}/reject'.format(self.package['id']), status=403))

    def test_dataset_reject_403_for_member(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'paul'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/reject'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    def test_dataset_reject_403_for_editor(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'john'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/reject'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_reject_302_for_admin(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/reject'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        assert resp.status_int, 302

    def test_dataset_approve_403_for_anonimous_users(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            app.get(url=url_for('/dataset-publish/{0}/approve'.format(self.package['id']), status=403))

    def test_dataset_approve_403_for_member(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'paul'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/approve'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    def test_dataset_approve_403_for_editor(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'john'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/approve'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_approve_302_for_admin(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/approve'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        assert resp.status_int, 302

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_approve_and_publish_for_admin(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        updated = helpers.call_action('package_show', {'user': 'george'}, **{'id': self.package['id']})
        # Make sure it's private before call
        assert updated['private']
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/approve?make_public=true'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        updated = helpers.call_action('package_show', {'user': 'george'}, **{'id': self.package['id']})
        assert not updated['private']

    def test_dataset_resubmit_403_for_anonimous_users(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            app.get(url=url_for('/dataset-publish/{0}/resubmit'.format(self.package['id']), status=403))

    def test_dataset_resubmit_403_for_member(self):
        app = self._get_test_app()
        with assert_raises(toolkit.NotAuthorized) as e:
            extra_environ = {'REMOTE_USER': 'paul'.encode('ascii')}
            app.get(url=url_for(
                '/dataset-publish/{0}/resubmit'.format(self.package['id'])),
                extra_environ=extra_environ
            )

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_resubmit_302_for_editor(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'john'}
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/resubmit'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        assert resp.status_int, 302

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_resubmit_302_for_admin(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        resp = app.get(url=url_for(
            '/dataset-publish/{0}/resubmit'.format(self.package['id'])),
            extra_environ=extra_environ
        )
        assert resp.status_int, 302


class TestWorkflowActivityStream(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):

        helpers.reset_db()
        super(TestWorkflowActivityStream, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        super(TestWorkflowActivityStream, cls).teardown_class()
        helpers.reset_db()

    def setup(self):
        super(TestWorkflowActivityStream, self).setup()
        self.pkg = 'test-dataset-1'
        helpers.reset_db()
        rebuild()
        factories.User(name='george', id='george')
        factories.User(name='john', id='john')
        factories.User(name='paul', id='paul')
        factories.Organization(
            users=[
                {'name': 'george', 'capacity': 'admin'},
                {'name': 'john', 'capacity': 'editor'},
                {'name': 'paul', 'capacity': 'reader'}
            ],
            name='us-ed-1',
            id='us-ed-1'
        )
        # Dataset created by factories seem to use sysadmin so approval_state
        # forced to be "approved". Creating packages this way to avoid that
        context = {'user': 'john'}
        data_dict = _create_dataset_dict(self.pkg, 'us-ed-1')
        self.package = helpers.call_action('package_create', context, **data_dict)


    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_workflow_tab_admin_can_see(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        assert 'Workflow Activity' in resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_workflow_tab_editor_can_see(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'john'}
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        assert 'Workflow Activity' in resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_admin_can_see_submitted_for_review_in_activity_stream(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        exp = 'requested a review for new dataset <span><a href="/dataset/{0}">{0}</a></span>'
        assert exp.format(self.package['name']) in resp, resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_editor_can_see_submitted_for_review_in_activity_stream(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'john'}
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        exp = 'requested a review for new dataset <span><a href="/dataset/{0}">{0}</a></span>'
        assert exp.format(self.package['name']) in resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_admin_can_see_approved_in_activity_stream(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        app.get(url=url_for(
                    '/dataset-publish/{0}/approve'.format(self.package['id'])),
                    extra_environ=extra_environ)
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        exp = 'approved dataset <span><a href="/dataset/{0}">{0}</a></span> for publication'
        assert exp.format(self.package['name']) in resp, resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_editor_can_see_approved_in_activity_stream(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        app.get(url=url_for(
                    '/dataset-publish/{0}/approve'.format(self.package['id'])),
                    extra_environ=extra_environ)
        extra_environ = {'REMOTE_USER': 'john'}
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        exp = 'approved dataset <span><a href="/dataset/{0}">{0}</a></span> for publication'
        assert exp.format(self.package['name']) in resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_admin_can_see_rejected_in_activity_stream(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        app.get(url=url_for(
                    '/dataset-publish/{0}/reject'.format(self.package['id'])),
                    extra_environ=extra_environ)
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        exp = 'rejected dataset <span><a href="/dataset/{0}">{0}</a></span> for publication'
        assert exp.format(self.package['name']) in resp, resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_editor_can_see_rejected_in_activity_stream(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        app.get(url=url_for(
                    '/dataset-publish/{0}/reject'.format(self.package['id'])),
                    extra_environ=extra_environ)
        extra_environ = {'REMOTE_USER': 'john'}
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        exp = 'rejected dataset <span><a href="/dataset/{0}">{0}</a></span> for publication'
        assert exp.format(self.package['name']) in resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_admin_can_see_resubmited_in_activity_stream(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        app.get(url=url_for(
                    '/dataset-publish/{0}/reject'.format(self.package['id'])),
                    extra_environ=extra_environ)
        extra_environ = {'REMOTE_USER': 'john'}
        app.get(url=url_for(
                    '/dataset-publish/{0}/resubmit'.format(self.package['id'])),
                    extra_environ=extra_environ)
        extra_environ = {'REMOTE_USER': 'george'}
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        exp = 'made changes and requested a review for dataset <span><a href="/dataset/{0}">{0}</a></span>'
        assert exp.format(self.package['name']) in resp, resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_dataset_editor_can_see_resubmited_in_activity_stream(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        app.get(url=url_for(
                    '/dataset-publish/{0}/reject'.format(self.package['id'])),
                    extra_environ=extra_environ)
        extra_environ = {'REMOTE_USER': 'john'}
        app.get(url=url_for(
                    '/dataset-publish/{0}/resubmit'.format(self.package['id'])),
                    extra_environ=extra_environ)
        resp = app.get(url=url_for(
            '/dataset/workflow/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        exp = 'made changes and requested a review for dataset <span><a href="/dataset/{0}">{0}</a></span>'
        assert exp.format(self.package['name']) in resp

    @mock.patch('ckanext.ed.mailer.mail_user')
    @mock.patch('ckanext.ed.mailer.render_jinja2')
    def test_make_sure_approval_state_not_visible_in_normal_activity_stream(self, mock_jinja2, mock_mail_user):
        app = self._get_test_app()
        extra_environ = {'REMOTE_USER': 'george'}
        app.get(url=url_for(
                    '/dataset-publish/{0}/approve'.format(self.package['id'])),
                    extra_environ=extra_environ)
        extra_environ = {'REMOTE_USER': 'john'}
        resp = app.get(url=url_for(
            '/dataset/activity/{0}?id={1}'.format(self.package['name'], self.package['id']),
        ),extra_environ=extra_environ)
        assert 'approval_state' not in resp


def _create_dataset_dict(package_name, office_name='us-ed', private=False):
    return {
        'name': package_name,
        'contact_name': 'Stu Shepard',
        'program_code': '321',
        'access_level': 'public',
        'bureau_code': '123',
        'contact_email': '%s@email.com' % package_name,
        'notes': 'notes',
        'owner_org': office_name,
        'title': package_name.upper(),
        'identifier': 'identifier',
        'private': private
    }
