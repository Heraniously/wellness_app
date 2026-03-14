from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# This tells Django to look for the "static" folder in your root directory
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# 1. Turn off Debug
DEBUG = False

# 2. Add your domain name (e.g., 'yourdomain.com')
ALLOWED_HOSTS = [
    'HeranKim.pythonanywhere.com',
    '127.0.0.1',
    'localhost',
]

# The URL used when referring to static files
STATIC_URL = 'static/'

# This is the physical location on the PythonAnywhere server
STATIC_ROOT = '/home/Heraniously/mobile_web_dev/thesis/wellness_app/static'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-0k)ee$-8!e(ex3c^s!tuc&bozx+y^x21#(_ddcn5n*yis3mu_z'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'scheduling',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'scheduling.context_processors.current_time',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# core/settings.py

# A more robust way to check if we are on PythonAnywhere
on_pythonanywhere = 'PYTHONANYWHERE_DOMAIN' in os.environ

if on_pythonanywhere:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    # While we are here, let's fix the STATIC_ROOT to be absolute for PA
    STATIC_ROOT = '/home/HeranKim/mobile_web_dev/thesis/wellness_app/staticfiles'
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'wellness_db',
            'USER': 'wellness_user',
            'PASSWORD': 'well_pass123',
            'HOST': '127.0.0.1',
            'PORT': '3306',
        }
    }
    STATIC_ROOT = BASE_DIR / 'staticfiles'


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Bucharest'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'class_list'