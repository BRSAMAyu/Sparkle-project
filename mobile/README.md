# Mobile Notes

## Codegen
If generated mocks or JSON serializers are missing, run:

```bash
dart run build_runner build --delete-conflicting-outputs
```

## macOS Build Issues
If you encounter build errors related to `gcc` or `g++` on macOS (especially if you use Homebrew), you may need to unset `CC` and `CXX` environment variables before building:

```bash
unset CC CXX
flutter run
```