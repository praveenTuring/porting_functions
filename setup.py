from setuptools import find_packages, setup

setup(
    name="portal_functions",
    author="App Scaling",
    description="Porting functions library ",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent" "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.10",
    setup_requires=["setuptools-git-versioning"],
    version_config={
        "dirty_template": "{tag}",
    },
)
