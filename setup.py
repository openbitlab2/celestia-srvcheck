from setuptools import setup

import srvcheck

setup(name='celestia-srvcheck',
	version=srvcheck.__version__,
	description='',
	author='Davide Gessa',
	setup_requires='setuptools',
	author_email='gessadavide@gmail.com',
	packages=[
		'srvcheck',
		'srvcheck.chains',
		'srvcheck.utils',
		'srvcheck.tasks',
		'srvcheck.notification'
	],
	entry_points={
		'console_scripts': [
			'srvcheck=srvcheck.main:main',
			'srvcheck-defaultconf=srvcheck.main:defaultConf'
		],
	},
    zip_safe=False,
	install_requires=['requests', 'packaging==21.3', 'python-dateutil', 'matplotlib'],
)