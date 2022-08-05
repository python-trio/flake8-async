# Changelog
*[CalVer, YY.month.patch](https://calver.org/)*

## 22.8.1
- Added TRIO109: Async definitions should not have a `timeout` parameter. Use `trio.[fail/move_on]_[at/after]`
- Added TRIO110: `while <condition>: await trio.sleep()` should be replaced by a `trio.Event`.

## 22.7.6
- Extend TRIO102 to also check inside `except BaseException` and `except trio.Cancelled`
- Extend TRIO104 to also check for `yield`
- Update error messages on TRIO102 and TRIO103

## 22.7.5
- Add TRIO103: `except BaseException` or `except trio.Cancelled` with a code path that doesn't re-raise
- Add TRIO104: "Cancelled and BaseException must be re-raised" if user tries to return or raise a different exception.
- Added TRIO107: Async functions must have at least one checkpoint on every code path, unless an exception is raised
- Added TRIO108: Early return from async function must have at least one checkpoint on every code path before it.

## 22.7.4
- Added TRIO105 check for not immediately `await`ing async trio functions.
- Added TRIO106 check that trio is imported in a form that the plugin can easily parse.

## 22.7.3
- Added TRIO102 check for unsafe checkpoints inside `finally:` blocks

## 22.7.2
- Avoid `TRIO100` false-alarms on cancel scopes containing `async for` or `async with`.

## 22.7.1
- Initial release with TRIO100 and TRIO101
