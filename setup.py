from setuptools import setup, find_packages

version = '0.0.1dev'

long_description = (open('README.rst').read() +
    '\n\n' + open('HISTORY.txt').read())


setup(name='GLShell',
      version=version,
      description="Terminal emulator enhanced with OpenGL rendering",
      long_description=long_description,
      author="Aaron D Vose",
      author_email="avose@aaronvose.net",
      url="https://github.com/avose/GLShell",
      license="LGPL",
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          'setuptools',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
