# End-to-end flow benchmark

Synthetic HTTP, real PostgreSQL and default logging/reporting; at least five samples per scenario.

| Scenario | Samples | Median seconds | Minimum | Maximum | MAD |
|---|---:|---:|---:|---:|---:|
| initial | 5 | 0.060336 | 0.059565 | 0.065734 | 0.000771 |
| skip_all | 5 | 0.013344 | 0.012137 | 0.014329 | 0.000786 |
| middle_failed | 5 | 0.022869 | 0.021627 | 0.024255 | 0.001214 |
| partial_expired | 5 | 0.043947 | 0.041845 | 0.044296 | 0.000349 |
| refresh_all | 5 | 0.061498 | 0.060498 | 0.064119 | 0.000396 |
| append_update | 5 | 0.060975 | 0.058507 | 0.067188 | 0.002467 |
| mutable_delete | 5 | 0.020446 | 0.019958 | 0.021229 | 0.000267 |
| mutable_reappear | 5 | 0.020822 | 0.020584 | 0.021857 | 0.000238 |
| empty | 5 | 0.050835 | 0.049967 | 0.053688 | 0.000646 |
| duplicates | 5 | 0.055743 | 0.055013 | 0.057660 | 0.000643 |
| partial_failure | 5 | 0.049003 | 0.047843 | 0.051769 | 0.001160 |
| long_report | 5 | 0.974860 | 0.894914 | 0.996531 | 0.021010 |
