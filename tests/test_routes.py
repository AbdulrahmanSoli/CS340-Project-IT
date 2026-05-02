import os
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('DATABASE_URL', 'postgresql://example.invalid/db')

from app import app


class RouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def login_session(self, user_id=1, user_type='Admin', user_name='Test User'):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['user_type'] = user_type
            sess['user_name'] = user_name
            sess['csrf_token'] = 'csrf-test-token'

    def test_post_without_csrf_is_rejected(self):
        response = self.client.post('/login', data={
            'email': 'admin@example.com',
            'password': 'secret',
        })

        self.assertEqual(response.status_code, 400)

    def test_login_sets_session_with_hashed_password(self):
        hashed = generate_password_hash('secret')

        with patch('routes.auth.query', return_value=[(1, 'Admin User', hashed, 'Admin')]):
            self.client.get('/login')
            with self.client.session_transaction() as sess:
                token = sess['csrf_token']

            response = self.client.post('/login', data={
                'csrf_token': token,
                'email': 'admin@example.com',
                'password': 'secret',
            })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/dashboard')
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['user_id'], 1)
            self.assertEqual(sess['user_name'], 'Admin User')
            self.assertEqual(sess['user_type'], 'Admin')

    def test_database_url_rejects_placeholder_host(self):
        from db import _database_url

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:password@host:5432/dbname'}):
            with self.assertRaisesRegex(RuntimeError, 'placeholder host'):
                _database_url()

    def test_admin_nav_hides_history_link(self):
        self.login_session(user_type='Admin')

        with patch('routes.assets.query', return_value=[]):
            response = self.client.get('/assets')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('/users', body)
        self.assertNotIn('/history', body)

    def test_employee_cannot_open_admin_users_page(self):
        self.login_session(user_id=3, user_type='Employee')

        response = self.client.get('/users')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/dashboard')

    def test_employee_admin_asset_filter_redirects_to_dashboard(self):
        self.login_session(user_id=3, user_type='Employee')

        response = self.client.get('/assets/filter?status=Available')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/dashboard')

    def test_employee_admin_get_routes_redirect_to_dashboard(self):
        self.login_session(user_id=3, user_type='Employee')

        routes = [
            '/assets',
            '/assets/filter?status=Available',
            '/assets/assignments',
            '/assets/unassigned',
            '/assets/count-by-category',
            '/assets/frequent-assignments',
            '/assets/new-purchases',
            '/assignments',
            '/assignments/returned',
            '/assignments/details',
            '/assignments/avg-days',
            '/assignments/top-users',
            '/assignments/quick-returns',
            '/assignments/repeated-assets',
            '/users',
            '/users/filter?type=Admin',
            '/users/filter?type=Employee',
            '/users/assets-count',
            '/users/no-active-asset',
            '/users/department-count',
            '/users/most-assignments',
            '/users/type-count',
        ]

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers['Location'], '/dashboard')

    def test_employee_can_open_own_assignments_page(self):
        self.login_session(user_id=3, user_type='Employee')

        with patch('routes.assignments.query', return_value=[]):
            response = self.client.get('/assignments/employee/3')

        self.assertEqual(response.status_code, 200)

    def test_employee_my_assignments_hides_admin_assignment_links(self):
        self.login_session(user_id=3, user_type='Employee')

        rows = [(7, '2026-05-01', None, 10, 3, 1, 'Dell Laptop', 'Employee User')]
        with patch('routes.assignments.query', return_value=rows):
            response = self.client.get('/assignments/employee/3')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<h2>My Assignments</h2>', body)
        self.assertIn('Dell Laptop (#10)', body)
        self.assertNotIn("href='/assignments'>Active</a>", body)
        self.assertNotIn("href='/assignments/returned'", body)
        self.assertNotIn('/assignments/add', body)
        self.assertNotIn('Mark Returned', body)

    def test_employee_my_assets_hides_admin_asset_filters(self):
        self.login_session(user_id=3, user_type='Employee')

        rows = [(10, 'Dell Laptop', 'Laptop', 'Assigned', 'SER-10')]
        with patch('routes.assets.query', return_value=rows):
            response = self.client.get('/assets/my')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<h2>My Assets</h2>', body)
        self.assertIn('Dell Laptop', body)
        self.assertNotIn('/assets/filter?status=Available', body)
        self.assertNotIn('/assets/unassigned', body)
        self.assertNotIn('Category contains', body)
        self.assertNotIn('Mark Damaged', body)

    def test_assign_asset_rejects_non_available_asset_before_tx(self):
        self.login_session(user_type='Admin')

        with patch('routes.assignments.query') as mock_query, patch('routes.assignments.tx') as mock_tx:
            mock_query.side_effect = [
                [('Assigned',)],
                [],
                [],
                [],
            ]
            response = self.client.post('/assignments/add', data={
                'csrf_token': 'csrf-test-token',
                'asset_id': '10',
                'user_id': '3',
            })

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Asset 10 is not available for assignment.', body)
        mock_tx.assert_not_called()

    def test_avg_days_displays_zero_when_no_returns_exist(self):
        self.login_session(user_type='Admin')

        with patch('routes.assignments.query', return_value=[(None,)]):
            response = self.client.get('/assignments/avg-days')

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('Average days asset kept: <strong>0</strong>', body)
        self.assertNotIn('No assignments found.', body)

    def test_assignment_table_renders_asset_and_employee_names(self):
        self.login_session(user_type='Admin')

        rows = [(7, '2026-05-01', None, 10, 3, 1, 'Dell Laptop', 'Employee User')]
        with patch('routes.assignments.query', side_effect=[rows, [], []]):
            response = self.client.get('/assignments')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Dell Laptop (#10)', body)
        self.assertIn('Employee User (#3)', body)

    def test_asset_filter_preserves_form_values(self):
        self.login_session(user_type='Admin')

        with patch('routes.assets.query', return_value=[]):
            response = self.client.get('/assets/filter?status=Damaged&category=Laptop&serial=ABC')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("value='Laptop'", body)
        self.assertIn("value='ABC'", body)
        self.assertIn("value='Damaged' selected", body)

    def test_dashboard_renders_counts_and_recent_assignments(self):
        self.login_session(user_type='Admin', user_name='Admin User')

        with patch('routes.auth.query') as mock_query:
            mock_query.side_effect = [
                [(12,)],
                [(7, 4, 1)],
                [('Dell Laptop', 'Employee User', '2026-05-01')],
            ]
            response = self.client.get('/dashboard')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Welcome, Admin User', body)
        self.assertIn('Total: 12', body)
        self.assertIn('Available: 7', body)
        self.assertIn('Assigned: 4', body)
        self.assertIn('Damaged: 1', body)
        self.assertIn('Dell Laptop', body)
        self.assertEqual(mock_query.call_count, 3)

    def test_employee_dashboard_renders_only_employee_assignments(self):
        self.login_session(user_id=3, user_type='Employee', user_name='Employee User')

        with patch('routes.auth.query') as mock_query:
            mock_query.side_effect = [
                [(2,)],
                [('Dell Laptop', '2026-05-01')],
            ]
            response = self.client.get('/dashboard')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Welcome, Employee User', body)
        self.assertIn('My Assets Overview', body)
        self.assertIn('Currently assigned: 2', body)
        self.assertIn('My Recent Assignments', body)
        self.assertIn('Dell Laptop', body)
        self.assertNotIn('Available:', body)
        self.assertNotIn('Employee</th>', body)
        self.assertEqual(mock_query.call_count, 2)

    def test_logout_get_does_not_clear_session(self):
        self.login_session(user_type='Admin')

        response = self.client.get('/logout')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/dashboard')
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['user_type'], 'Admin')

    def test_logout_post_clears_session(self):
        self.login_session(user_type='Admin')

        response = self.client.post('/logout', data={
            'csrf_token': 'csrf-test-token',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/login')
        with self.client.session_transaction() as sess:
            self.assertNotIn('user_id', sess)

    def test_asset_list_renders_row_level_status_actions(self):
        self.login_session(user_type='Admin')

        rows = [
            (1, 'Laptop A', 'Laptop', 'Available', 'SER-1'),
            (2, 'Monitor B', 'Monitor', 'Damaged', 'SER-2'),
            (3, 'Phone C', 'Phone', 'Assigned', 'SER-3'),
        ]
        with patch('routes.assets.query', return_value=rows) as mock_query:
            response = self.client.get('/assets')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Mark Damaged', body)
        self.assertIn('Mark Available', body)
        self.assertIn('Assigned', body)
        self.assertIn('ORDER BY status, assetName, assetID', mock_query.call_args[0][0])

    def test_update_asset_status_writes_history_in_transaction(self):
        self.login_session(user_id=1, user_type='Admin')

        with patch('routes.assets.query') as mock_query, patch('routes.assets.tx') as mock_tx:
            mock_query.side_effect = [
                [('Available',)],
                [(9,)],
            ]
            response = self.client.post('/assets/update', data={
                'csrf_token': 'csrf-test-token',
                'asset_id': '10',
                'status': 'Damaged',
            })

        self.assertEqual(response.status_code, 302)
        statements = mock_tx.call_args[0][0]
        self.assertEqual(len(statements), 2)
        self.assertIn('UPDATE asset SET status', statements[0][0])
        self.assertIn('INSERT INTO asset_status_history', statements[1][0])
        self.assertEqual(statements[1][1], (9, 'Available', 'Damaged', '10', 1))

    def test_assign_asset_success_uses_transaction_for_assignment_and_history(self):
        self.login_session(user_id=1, user_type='Admin')

        with patch('routes.assignments.query') as mock_query, patch('routes.assignments.tx') as mock_tx:
            mock_query.side_effect = [
                [('Available',)],
                [(1,)],
                [(12,)],
                [(22,)],
            ]
            response = self.client.post('/assignments/add', data={
                'csrf_token': 'csrf-test-token',
                'asset_id': '10',
                'user_id': '3',
            })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/assignments')
        statements = mock_tx.call_args[0][0]
        self.assertEqual(len(statements), 3)
        self.assertIn('INSERT INTO asset_assignment', statements[0][0])
        self.assertIn('UPDATE asset SET status', statements[1][0])
        self.assertIn('INSERT INTO asset_status_history', statements[2][0])
        self.assertEqual(statements[0][1], (12, '10', '3', 1))
        self.assertEqual(statements[2][1], (22, 'Available', 'Assigned', '10', 1))

    def test_return_asset_success_uses_transaction_for_return_and_history(self):
        self.login_session(user_id=1, user_type='Admin')

        with patch('routes.assignments.query') as mock_query, patch('routes.assignments.tx') as mock_tx:
            mock_query.side_effect = [
                [(10, 'Assigned', None)],
                [(23,)],
            ]
            response = self.client.post('/assignments/return/7', data={
                'csrf_token': 'csrf-test-token',
            })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/assignments')
        statements = mock_tx.call_args[0][0]
        self.assertEqual(len(statements), 3)
        self.assertIn('UPDATE asset_assignment SET returnDate', statements[0][0])
        self.assertIn('UPDATE asset SET status', statements[1][0])
        self.assertIn('INSERT INTO asset_status_history', statements[2][0])
        self.assertEqual(statements[2][1], (23, 'Assigned', 'Available', 10, 1))

    def test_add_user_hashes_password_and_inserts_role_table(self):
        self.login_session(user_type='Admin')

        with patch('routes.users.tx') as mock_tx:
            response = self.client.post('/users/add', data={
                'csrf_token': 'csrf-test-token',
                'user_id': '5',
                'name': 'New Employee',
                'email': 'new@example.com',
                'dept': 'IT',
                'password': 'secret',
                'type': 'Employee',
            })

        self.assertEqual(response.status_code, 302)
        statements = mock_tx.call_args[0][0]
        self.assertEqual(len(statements), 2)
        self.assertIn('INSERT INTO users', statements[0][0])
        self.assertIn('INSERT INTO employee', statements[1][0])
        user_params = statements[0][1]
        self.assertEqual(user_params[:4], ('5', 'New Employee', 'new@example.com', 'IT'))
        self.assertTrue(user_params[4].startswith(('scrypt:', 'pbkdf2:')))
        self.assertEqual(user_params[5], 'Employee')

    def test_delete_asset_stops_when_active_assignment_exists(self):
        self.login_session(user_type='Admin')

        with patch('routes.assets.query') as mock_query:
            mock_query.side_effect = [
                [(1,)],
                [(1,)],
                [],
            ]
            response = self.client.post('/assets/delete/10', data={
                'csrf_token': 'csrf-test-token',
            })

        self.assertEqual(response.status_code, 200)
        self.assertIn('has an active assignment', response.get_data(as_text=True))
        self.assertEqual(mock_query.call_count, 3)


if __name__ == '__main__':
    unittest.main()
