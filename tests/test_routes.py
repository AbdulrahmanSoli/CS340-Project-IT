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

    def test_admin_nav_shows_history_link(self):
        self.login_session(user_type='Admin')

        with patch('routes.assets.query', return_value=[]):
            response = self.client.get('/assets')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('/users', body)
        self.assertIn('/history', body)

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
            '/history',
            '/history/asset?asset_id=10',
            '/history/asset/10',
            '/history/filter?status=Available',
            '/history/with-assets',
            '/history/count-by-asset',
            '/history/damaged',
            '/history/latest',
            '/history/frequent',
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

    def test_logged_out_history_redirects_to_login(self):
        response = self.client.get('/history')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/login')

    def test_employee_history_post_routes_redirect_to_dashboard(self):
        self.login_session(user_id=3, user_type='Employee')

        add_response = self.client.post('/history/add', data={
            'csrf_token': 'csrf-test-token',
            'history_id': '20',
            'asset_id': '10',
            'prev_status': 'Available',
            'new_status': 'Damaged',
        })
        dates_response = self.client.post('/history/dates', data={
            'csrf_token': 'csrf-test-token',
            'from_date': '2026-05-01',
            'to_date': '2026-05-02',
        })

        self.assertEqual(add_response.status_code, 302)
        self.assertEqual(add_response.headers['Location'], '/dashboard')
        self.assertEqual(dates_response.status_code, 302)
        self.assertEqual(dates_response.headers['Location'], '/dashboard')

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

    def test_history_list_renders_rows_for_admin(self):
        self.login_session(user_type='Admin')

        rows = [(5, 'Available', 'Damaged', '2026-05-01', 10, 1)]
        with patch('routes.history.query', return_value=rows):
            response = self.client.get('/history')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Asset Status History', body)
        self.assertIn('<td>10</td>', body)
        self.assertIn('<td>Available</td>', body)
        self.assertIn('<td>Damaged</td>', body)

    def test_history_filter_validates_status(self):
        self.login_session(user_type='Admin')

        with patch('routes.history.query', return_value=[]):
            response = self.client.get('/history/filter?status=Broken')

        self.assertEqual(response.status_code, 200)
        self.assertIn('Invalid status filter.', response.get_data(as_text=True))

    def test_history_asset_lookup_redirects_to_asset_route(self):
        self.login_session(user_type='Admin')

        response = self.client.get('/history/asset?asset_id=10')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/history/asset/10')

    def test_history_date_filter_validates_order(self):
        self.login_session(user_type='Admin')

        with patch('routes.history.query', return_value=[]):
            response = self.client.post('/history/dates', data={
                'csrf_token': 'csrf-test-token',
                'from_date': '2026-05-02',
                'to_date': '2026-05-01',
            })

        self.assertEqual(response.status_code, 200)
        self.assertIn('From date must be before or equal to to date.', response.get_data(as_text=True))

    def test_history_add_inserts_status_change(self):
        self.login_session(user_id=1, user_type='Admin')

        with patch('routes.history.query', return_value=[] ) as mock_query:
            response = self.client.post('/history/add', data={
                'csrf_token': 'csrf-test-token',
                'history_id': '20',
                'asset_id': '10',
                'prev_status': 'Available',
                'new_status': 'Damaged',
            })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/history')
        sql, params = mock_query.call_args[0]
        self.assertIn('INSERT INTO asset_status_history', sql)
        self.assertEqual(params, ('20', 'Available', 'Damaged', '10', 1))

    def test_history_advanced_named_rows_render(self):
        self.login_session(user_type='Admin')

        rows = [('Dell Laptop', 'Available', 'Assigned', '2026-05-01')]
        with patch('routes.history.query', return_value=rows):
            response = self.client.get('/history/with-assets')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('History with Asset Names', body)
        self.assertIn('Dell Laptop', body)

    def test_dashboard_renders_counts_and_recent_assignments(self):
        self.login_session(user_type='Admin', user_name='Admin User')

        with patch('routes.auth.query') as mock_query:
            # 2 queries now: status breakdown + recent assignments. Total is computed in Python.
            mock_query.side_effect = [
                [(7, 4, 1)],
                [('Dell Laptop', 'Employee User', '2026-05-01')],
            ]
            response = self.client.get('/dashboard')

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('12', body)            # total = 7 + 4 + 1
        self.assertIn('7', body)
        self.assertIn('Dell Laptop', body)
        self.assertEqual(mock_query.call_count, 2)

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
            # 3 reads now: asset status, employee check, combined next-id query
            mock_query.side_effect = [
                [('Available',)],
                [(1,)],
                [(12, 22)],
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

        # Verify the combined next-id query is one round trip, not two
        next_id_sql = mock_query.call_args_list[2][0][0]
        self.assertIn('MAX(assignmentID)', next_id_sql)
        self.assertIn('MAX(historyID)', next_id_sql)

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


class QueryOptimizationTests(unittest.TestCase):
    """Focused tests verifying the 5 query optimizations behave as intended."""

    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def login_admin(self, user_id=1):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['user_type'] = 'Admin'
            sess['user_name'] = 'Admin'
            sess['csrf_token'] = 'csrf-test-token'

    # --- 1. Dashboard: 3 queries → 2 ---
    def test_dashboard_admin_makes_only_two_queries(self):
        self.login_admin()
        with patch('routes.auth.query') as mock_query:
            mock_query.side_effect = [
                [(5, 3, 2)],
                [('A', 'B', '2026-01-01')],
            ]
            response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_query.call_count, 2)
        # Total derived in Python = 5+3+2 = 10
        self.assertIn('10', response.get_data(as_text=True))

    def test_dashboard_total_handles_null_status_sums(self):
        # Empty asset table makes SUM return NULL — total must coerce to 0, not crash
        self.login_admin()
        with patch('routes.auth.query') as mock_query:
            mock_query.side_effect = [
                [(None, None, None)],
                [],
            ]
            response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

    # --- 2. NOT IN → NOT EXISTS ---
    def test_unassigned_assets_uses_not_exists(self):
        self.login_admin()
        with patch('routes.assets.query', return_value=[]) as mock_query:
            self.client.get('/assets/unassigned')
        sql = mock_query.call_args[0][0]
        self.assertIn('NOT EXISTS', sql)
        self.assertNotIn('NOT IN', sql)

    def test_no_active_asset_users_uses_not_exists(self):
        self.login_admin()
        with patch('routes.users.query', return_value=[]) as mock_query:
            self.client.get('/users/no-active-asset')
        sql = mock_query.call_args[0][0]
        self.assertIn('NOT EXISTS', sql)
        self.assertNotIn('NOT IN', sql)

    # --- 3. Sargable date filter ---
    def test_new_purchases_uses_range_predicate_not_extract(self):
        self.login_admin()
        with patch('routes.assets.query', return_value=[]) as mock_query:
            self.client.get('/assets/new-purchases')
        sql = mock_query.call_args[0][0]
        self.assertNotIn('EXTRACT(YEAR FROM purchaseDate)', sql)
        self.assertIn("DATE_TRUNC('year'", sql)
        self.assertIn('purchaseDate >=', sql)

    # --- 4. delete_user combines 3 existence checks into 1 ---
    def test_delete_user_uses_combined_existence_check(self):
        self.login_admin()
        with patch('routes.users.query') as mock_query, patch('routes.users.tx'):
            mock_query.side_effect = [
                [('Employee',)],          # user lookup
                [(False, False, False)],  # combined EXISTS check — no references
            ]
            response = self.client.post('/users/delete/9', data={
                'csrf_token': 'csrf-test-token',
            })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(mock_query.call_count, 2)
        existence_sql = mock_query.call_args_list[1][0][0]
        self.assertEqual(existence_sql.count('EXISTS('), 3)

    def test_delete_user_blocks_when_assignment_history_exists(self):
        self.login_admin()
        with patch('routes.users.query') as mock_query:
            mock_query.side_effect = [
                [('Employee',)],
                [(True, False, False)],
                [],
            ]
            response = self.client.post('/users/delete/9', data={
                'csrf_token': 'csrf-test-token',
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn('assignment history', response.get_data(as_text=True))

    def test_delete_user_blocks_when_assigned_by_exists(self):
        self.login_admin()
        with patch('routes.users.query') as mock_query:
            mock_query.side_effect = [
                [('Admin',)],
                [(False, True, False)],
                [],
            ]
            response = self.client.post('/users/delete/9', data={
                'csrf_token': 'csrf-test-token',
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn('assigned assets to others', response.get_data(as_text=True))

    def test_delete_user_blocks_when_status_history_exists(self):
        self.login_admin()
        with patch('routes.users.query') as mock_query:
            mock_query.side_effect = [
                [('Admin',)],
                [(False, False, True)],
                [],
            ]
            response = self.client.post('/users/delete/9', data={
                'csrf_token': 'csrf-test-token',
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn('logged status changes', response.get_data(as_text=True))

    # --- 5. assign_asset combines 2 MAX(id)+1 queries into 1 ---
    def test_assign_asset_uses_combined_next_id_query(self):
        self.login_admin()
        with patch('routes.assignments.query') as mock_query, patch('routes.assignments.tx'):
            mock_query.side_effect = [
                [('Available',)],
                [(1,)],
                [(50, 99)],   # combined: next_assignment, next_history in one row
            ]
            response = self.client.post('/assignments/add', data={
                'csrf_token': 'csrf-test-token',
                'asset_id': '10',
                'user_id': '3',
            })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(mock_query.call_count, 3)


if __name__ == '__main__':
    unittest.main()
