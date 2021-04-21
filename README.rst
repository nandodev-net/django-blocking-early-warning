=====
Blocking Early Warnings
=====

Blocking Early Warnings is a Django app for detecting and measuring possible anomalies
based on data queried from ooni. You can receive emails and have a nice dashboard to look for 
data in some input urls. You can also get email notifications when something goes out of normal


Quick start
-----------

1. Add "blocking_early_warnings" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'blocking_early_warnings',
    ]

2. Include the polls URLconf in your project urls.py like this::

    path('blocking_early_warnings/', include('blocking_early_warnings.urls')),

3. Run ``python manage.py migrate`` to create the early warnings models.

4. Start the development server and visit http://127.0.0.1:8000/admin/
   to manage your urls to be watched (you'll need the Admin app enabled).

5. Visit http://127.0.0.1:8000/blocking_early_warnings/ to participate in the poll.
