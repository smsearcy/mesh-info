Test Data Files
===============

This is the folder for sample data files for testing.

Any file named `sysinfo-*.json` will be tested when `pytest`
is executed.  Additionally, the script `/scripts/scrub_test_files.py`
can be used to generally anonymize a sample file for uploading.  This should
make it as easy as possible to verify that the parser works with all the
various nodes out in the wild.
