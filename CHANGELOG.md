# Changelog
*[CalVer, YY.month.patch](https://calver.org/)*

## Future
- Add TRIO103: `except BaseException` or `except trio.Cancelled` with a code path that doesn't re-raise
- Add TRIO104: "Cancelled and BaseException must be re-raised" if user tries to return or raise a different exception.

## 22.7.4
- Added TRIO105 check for not immediately `await`ing async trio functions.
- Added TRIO106 check that trio is imported in a form that the plugin can easily parse.

## 22.7.3
- Added TRIO102 check for unsafe checkpoints inside `finally:` blocks

## 22.7.2
- Avoid `TRIO100` false-alarms on cancel scopes containing `async for` or `async with`.

## 22.7.1
- Initial release with TRIO100 and TRIO101
