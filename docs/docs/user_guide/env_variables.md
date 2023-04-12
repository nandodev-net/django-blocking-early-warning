# Environment Variables

The docker app requieres some **environment variables** to specify how to wire things up on launch. These variables are located 
in environment `.env` files and every component of the app requires a specific environment. In this section we will explain which `.env` files
and variables we have and good defaults for a quick test launch.

We use the following environment files:

* `.env` : Provides config for the web server, which implements the main app.
* `.env.celery` : Configs for celery, the async task backend.
* `.env.db` : Configs for the postgres database backend.

## Default files

I this section we will explain about each file and its corresponding environment variables, and we will provide some useful default values 
you can use as well. 

!!! Note 
    You might need a Django secret key, you can generate one using [this site](https://djecrety.ir). 

### .env

```
DEBUG=1        # If this is a debug deployment, 1 for true, 0 for false
SECRET_KEY=your_django_secret_key            # Change with your own secret key
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1] nginx        
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:1337 https://localhost:1337 http://localhost:1337
SQL_ENGINE=django.db.backends.postgresql
SQL_DATABASE=early_warnings            # Change for your database name (the one you refer to when you connect to a DB)
SQL_USER=your_user_name                     # Change for your database username
SQL_PASSWORD=your_user_pass                 # Change for your database user password
SQL_HOST=postgres                           
SQL_PORT=5432
DATABASE=postgres
CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379
```

### .env.celery

```
DEBUG=1                                     # If this is a debug deployment, 1 for true, 0 for false
SECRET_KEY=your_django_secret_key           # Change with your own secret key
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1] redis

CSRF_TRUSTED_ORIGINS=http://127.0.0.1:1337 https://localhost:1337 http://localhost:1337
SQL_ENGINE=django.db.backends.postgresql
SQL_DATABASE=early_warnings            # Change for your database name (the one you refer to when you connect to a DB)
SQL_USER=your_user_name                     # Change for your database username
SQL_PASSWORD=your_user_pass                 # Change for your database user password
SQL_HOST=postgres
SQL_PORT=5432
DATABASE=postgres
CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379
```

### .env.db
POSTGRES_USER=your_user_name                # Change, Same as SQL_USER above
POSTGRES_PASSWORD=your_user_pass            # Change, Same as SQL_PASSWORD above
POSTGRES_DB=early_warnings             # Change, Same as SQL_DATABASE above

