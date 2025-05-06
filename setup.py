from setuptools import setup, find_packages

setup(
    name='terminalai',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'ai=terminalai.terminalai:main',
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
