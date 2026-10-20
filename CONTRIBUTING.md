# Contributing

Thanks for looking. rift-gate is small on purpose; changes that keep it small and checkable are the easiest to accept.

## Run the tests

```
pip install -e ".[test]"
python -m pytest
python examples/demo.py   # then `git diff examples/traces` should be empty
```

## Changing behavior

- Every change to what the gate decides needs a test that fails before the change and passes after.
- The gate must fail closed. A change that lets a malformed input, an unknown evidence age or an internal error result in `pass` will not be accepted.
- The gate never branches on who is calling or why. Same contract, same call, same state: same decision.

## Changing the contract format or schemas

Open an issue first describing the problem the change solves. Update `spec/boundary-contract.md`, `spec/boundary-contract.schema.json` and the example contracts together, and say whether existing contracts remain valid.

## Security-sensitive findings

If you find a way to get a forbidden or unverified action past the gate, please do not open a public issue first. Follow [SECURITY.md](SECURITY.md).

## License

By contributing you agree that your contributions are licensed under Apache-2.0.
