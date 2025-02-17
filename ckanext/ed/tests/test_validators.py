from nose.tools import assert_equals

from ckan import model
from ckan.tests import factories as core_factories
from ckan.tests.helpers import call_action, FunctionalTestBase


class TestValidators(FunctionalTestBase):
    def test_dataset_by_sysadmin_and_admin_is_not_approval_pending(self):
        core_factories.User(name='george')
        core_factories.Organization(
            users=[{'name': 'george', 'capacity': 'admin'}],
            name='us-ed-1',
            id='us-ed-1'
        )

        sysadmin = core_factories.Sysadmin()
        context = _create_context(sysadmin)
        data_dict = _create_dataset_dict('test-dataset-1', 'us-ed-1')
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-1')
        assert_equals(dataset.get('approval_state'), 'active')

        context = _create_context({'name': 'george'})
        data_dict = _create_dataset_dict('test-dataset-2', 'us-ed-1')
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset-2')
        assert_equals(dataset.get('approval_state'), 'active')


    def test_dataset_by_editor_is_approval_pending(self):
        core_factories.User(name='john')
        core_factories.Organization(
            users=[{'name': 'john', 'capacity': 'editor'}],
            name='us-ed-2',
            id='us-ed-2'
        )

        context = _create_context({'name': 'john'})
        data_dict = _create_dataset_dict('test-dataset', 'us-ed-2')
        call_action('package_create', context, **data_dict)
        dataset = call_action('package_show', context, id='test-dataset')
        assert_equals(dataset['approval_state'], 'approval_pending')


    def test_dataset_update_by_editor_remains_rejected(self):
        core_factories.User(name='george')
        core_factories.User(name='john')
        core_factories.Organization(
            users=[
                {'name': 'george', 'capacity': 'admin'},
                {'name': 'john', 'capacity': 'editor'}
            ],
            name='us-ed-3',
            id='us-ed-3'
        )

        context_editor = _create_context({'name': 'john'})
        data_dict = _create_dataset_dict('test-dataset', 'us-ed-3')
        package = call_action('package_create', context_editor, **data_dict)
        context_admin = _create_context({'name': 'george'})
        call_action(
            'package_patch',
            context_admin,
            **{'approval_state': 'rejected', 'id': package['id']}
        )
        data_dict['id'] = package['id']
        call_action('package_update', context_editor, **data_dict)
        dataset = call_action('package_show', context_editor, id='test-dataset')
        assert_equals(dataset['approval_state'], 'rejected')


    def test_dataset_update_by_editor_remains_approved(self):
        core_factories.User(name='george')
        core_factories.User(name='john')
        core_factories.Organization(
            users=[
                {'name': 'george', 'capacity': 'admin'},
                {'name': 'john', 'capacity': 'editor'}
            ],
            name='us-ed-4',
            id='us-ed-4'
        )

        context_editor = _create_context({'name': 'john'})
        data_dict = _create_dataset_dict('test-dataset', 'us-ed-4')
        package = call_action('package_create', context_editor, **data_dict)
        context_admin = _create_context({'name': 'george'})
        call_action(
            'package_patch',
            context_admin,
            **{'approval_state': 'approved', 'id': package['id']}
        )
        data_dict['id'] = package['id']
        call_action('package_update', context_editor, **data_dict)
        dataset = call_action('package_show', context_editor, id='test-dataset')
        assert_equals(dataset['approval_state'], 'approved')


def _create_context(user):
    return {'model': model, 'user': user['name']}


def _create_dataset_dict(package_name, office_name='us-ed'):
    return {
        'name': package_name,
        'contact_name': 'Stu Shepard',
        'program_code': '321',
        'access_level': 'public',
        'bureau_code': '123',
        'contact_email': '%s@email.com' % package_name,
        'notes': 'notes',
        'owner_org': office_name,
        'title': 'Title',
        'identifier': 'identifier'
    }
