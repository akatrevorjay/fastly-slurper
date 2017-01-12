SHORT_NAME = 'slurper'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s| '
                      '%(name)s/%(processName)s[%(process)d]-'
                      '%(threadName)s[%(thread)d]: '
                      '%(message)s '
                      '@%(funcName)s:%(lineno)d '
                      '#%(levelname)s',
        }
    },
    'handlers': {
        'console': {
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
    }
}
