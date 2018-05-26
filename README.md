# Purpose

Creates code for taking scores (e.g. as part of a prize competition) and normalizes judges' scores in an attempt to minimize scoring bias and comparing one judge's scores as directly as possible to another judge's scores by mapping them to the same normal distribution.


# Assumptions

This code was originally designed to do normalization of reviewer scores for U.S. Department of Energy Energy Efficiency and Renewable Energy (DOE EERE) Funding Opportunity Announcements (FOAs). As such, some hard-coded assumptions about data inputs are present that would need to be modified if not using a DOE EERE application management system.

## Data Needed

For those DOE EERE users wishing to use this code, the input data it assumes will be used can be pulled from EERE eXCHANGE by logging in (as FOA Manager of the FOA in question), selecting Reports -> Review Details Grid, and saving the results as a CSV file in the same folder as the iPython notebook in this repo (the \*.ipynb file).