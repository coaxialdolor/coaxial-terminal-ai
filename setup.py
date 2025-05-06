from setuptools import setup

setup(
    name='terminalai',
    version='0.1.0',
    py_modules=['terminalai'],
    install_requires=[],
    entry_points={
        'console_scripts': [
            'ai=terminalai:main',
        ],
    },
    author='Your Name',
    description='TerminalAI: Command-line AI assistant',
    url='https://github.com/yourusername/terminalai',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)