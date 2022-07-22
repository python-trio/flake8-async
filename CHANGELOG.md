# Changelog
*[CalVer, YY.month.patch](https://calver.org/)*

## 22.7.3
Added:
- **TRIO102** `await` in `finally` must have a cancel scope with shielding.

## 22.7.2
- Avoid `TRIO100` false-alarms on cancel scopes containing `async for` or `async with`.

## 22.7.1
- Initial release with TRIO100 and TRIO101
