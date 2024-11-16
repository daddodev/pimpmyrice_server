import setuptools

with open("README.md", "r", encoding="utf8") as f:
    long_description = f.read()

setuptools.setup(
    name="pimpmyrice_server",
    version="0.1.0",
    author="daddodev",
    author_email="daddodev@gmail.com",
    description="Server for PimpMyRice",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/daddodev/pimpmyrice_server",
    # project_urls={
    #     "Bug Tracker": "https://github.com/pypa/sampleproject/issues",
    # },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["pimp-server=pimpmyrice_server.__main__:main"]},
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    package_data={
        "pimpmyrice_server": ["assets/pimp.ico"],
    },
    python_requires=">=3.12",
    install_requires=[
        "pimpmyrice",
        "fastapi",
        "uvicorn[standard]",
        "docopt",
        "requests",
        "watchdog",
        "pystray",
    ],
)
