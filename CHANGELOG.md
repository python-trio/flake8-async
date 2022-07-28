# Changelog
*[CalVer, YY.month.patch](https://calver.org/)*

## 22.7.5
- Added TRIO105 check for not `await`ing async trio functions.

## 22.7.3
- Added TRIO102 check for unsafe checkpoints inside `finally:` blocks

## 22.7.2
- Avoid `TRIO100` false-alarms on cancel scopes containing `async for` or `async with`.

## 22.7.1
- Initial release with TRIO100 and TRIO101
