# Changelog

## v1.2.0 (2023-07-11)

- Added support for sequence search and sequence motif search
- Updated Terminal class to allow for various types of searches
- Documentation and code update

## v1.1.0 (2023-06-20)

- Added support for including computed structure models (CSMs) in search (via `results_content_type`)
- Added support for chemical attribute search
- Documentation and code cleanup

## v1.0.0 (2023-06-08)

- Project forked from [sbliven/rcsbsearch](https://github.com/sbliven/rcsbsearch) into RCSB PDB GitHub organization as `rcsbsearchapi`
- Updated schema from v1 to v2
- Additional bug fixes

## v0.2.3 (2021-04-28)

- Fix mug with missing schema files when installed via pip
- Add jupyter notebooks
- Try rcsbsearch live with binder

## v0.2.2 (2021-04-06)

- Remove `in` operator syntax (incompatible with python spec)
- Fix import error due to schema change
- Ship schema with the package for stability and performance

## v0.2.1 (2020-06-18)

- Test release process

## v0.2.0 (2020-06-18)

- Add fluent syntax (originally called builder syntax)
  - Add PartialQuery helper
- Improve docs & automated testing

## v0.1.0 (2020-06-03)

- Ship it!
- Support for text searches