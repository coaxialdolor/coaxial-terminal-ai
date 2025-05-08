from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='coaxial-terminal-ai',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pygments',
        'rich',
    ],
    entry_points={
        'console_scripts': [
            'ai=terminalai.terminalai_cli:main',
        ],
    },
    author='coaxialdolor',
    author_email='your.email@example.com',  # Replace with your email
    description='TerminalAI: Command-line AI assistant',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/coaxialdolor/terminalai',
    project_urls={
        "Bug Tracker": "https://github.com/coaxialdolor/terminalai/issues",
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Utilities',
    ],
    python_requires='>=3.7',
)
