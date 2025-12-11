from setuptools import setup, find_packages

setup(
    name="bluetoothrc",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "kivy>=2.2.1",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="Bluetooth RC Car Controller",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Android",
    ],
    python_requires=">=3.7",
)
