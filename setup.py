from setuptools import setup, find_packages

with open('README.md') as readme_file:
    README = readme_file.read()

setup_args = dict(
    name='fakermaker',
    version='0.1.2',
    description='Creates pandas dataframes containing fake data using a IPython magic function with custom domain specific language',
    long_description_content_type="text/markdown",
    long_description=README,
    license='MIT',
    packages=find_packages(),
    author='Nicholas Miller',
    author_email='miller.nicholas.a@gmail.com',
    keywords=['FakerMaker', 'faker', 'fake data', 'generator', 'maker'],
    url='https://github.com/cassova/Faker-Maker',
    download_url='https://github.com/cassova/Faker-Maker'
)

install_requires = [
    'IPython',
    'numpy',
    'pandas',
    'Faker'
]

if __name__ == '__main__':
    setup(**setup_args, install_requires=install_requires)
