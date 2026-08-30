# UC freshman admit-rate gap, domestic vs international, 2018-2024.
# Pure Python. No pandas, no imports, no data file needed.
#
# Numbers below are the freshman applicant and admit counts from
# uc_admissions_summary_by_ethnicity.csv, already summed into two groups:
#   International, and Domestic (every other ethnicity category combined).
# Each row is:  year: (domestic applicants, domestic admits,
#                      international applicants, international admits)

DATA = {
    "Berkeley": {
        2018: (72545, 11848, 17064, 1453),
        2019: (70363, 12734, 17035, 1543),
        2020: (70959, 13923, 17105, 1467),
        2021: (91854, 14604, 20981, 1691),
        2022: (105097, 13268, 23113, 1254),
        2023: (104055, 13510, 21855, 1167),
        2024: (101995, 12904, 22247, 735),
    },
    "Davis": {
        2018: (62517, 23400, 15507, 8646),
        2019: (61571, 23470, 16522, 6888),
        2020: (61148, 26308, 15755, 9337),
        2021: (70518, 31362, 16618, 11112),
        2022: (76196, 27528, 18552, 7849),
        2023: (76597, 30561, 18041, 8839),
        2024: (80282, 31934, 18582, 9419),
    },
    "Irvine": {
        2018: (77555, 20583, 17504, 6752),
        2019: (77495, 18051, 18070, 7309),
        2020: (80474, 21587, 17464, 7714),
        2021: (89726, 24296, 18217, 6813),
        2022: (99132, 20964, 20062, 4244),
        2023: (101916, 24859, 19185, 6097),
        2024: (103364, 26882, 19335, 8163),
    },
    "Los Angeles": {
        2018: (94336, 13757, 19419, 2213),
        2019: (92669, 12155, 18652, 1565),
        2020: (90981, 13948, 17889, 1654),
        2021: (117605, 13055, 21877, 1973),
        2022: (126274, 11509, 23527, 1335),
        2023: (123904, 11427, 21999, 1309),
        2024: (124231, 11736, 22041, 1378),
    },
    "Merced": {
        2018: (23923, 16081, 1208, 547),
        2019: (24030, 17613, 1394, 681),
        2020: (24386, 21114, 1537, 868),
        2021: (25970, 22985, 1823, 1084),
        2022: (27604, 25281, 2316, 1485),
        2023: (27422, 24821, 2810, 1777),
        2024: (27814, 25600, 4114, 3306),
    },
    "Riverside": {
        2018: (45297, 22879, 3782, 1941),
        2019: (44608, 25205, 4908, 2779),
        2020: (44747, 29267, 4695, 3255),
        2021: (47834, 30861, 4843, 3576),
        2022: (49079, 33265, 5605, 4298),
        2023: (50956, 35107, 5987, 4651),
        2024: (52042, 39307, 6006, 5036),
    },
    "San Diego": {
        2018: (78149, 23741, 19749, 5687),
        2019: (79266, 25541, 19858, 5659),
        2020: (80788, 30254, 19274, 6379),
        2021: (97250, 34000, 21133, 6496),
        2022: (108170, 27583, 23059, 3519),
        2023: (108926, 28268, 21909, 3793),
        2024: (112650, 31054, 21800, 4862),
    },
    "Santa Barbara": {
        2018: (76255, 24252, 16051, 5472),
        2019: (76368, 21760, 17078, 5866),
        2020: (74313, 28136, 16648, 5248),
        2021: (88072, 26011, 17559, 4812),
        2022: (92061, 24961, 18934, 3727),
        2023: (93356, 27035, 17515, 3769),
        2024: (93076, 31160, 17183, 5187),
    },
    "Santa Cruz": {
        2018: (49598, 21594, 7027, 5209),
        2019: (48103, 22981, 7762, 5647),
        2020: (47854, 30177, 7214, 5414),
        2021: (55589, 31895, 6216, 4357),
        2022: (60051, 27690, 5963, 3236),
        2023: (62297, 39059, 6548, 3995),
        2024: (65261, 41937, 6461, 5249),
    },
}

YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
START, END = 2018, 2024


def rates(row):
    """Return (domestic admit rate, international admit rate) as percents."""
    dom_app, dom_adm, int_app, int_adm = row
    return 100.0 * dom_adm / dom_app, 100.0 * int_adm / int_app


def gap(campus, year):
    """Domestic admit rate minus international admit rate, in points."""
    dom, intl = rates(DATA[campus][year])
    return dom - intl


# ---------------------------------------------------------------- the answer
results = []
for campus in DATA:
    first = gap(campus, START)
    last = gap(campus, END)
    results.append((campus, first, last, last - first))

results.sort(key=lambda r: r[3], reverse=True)

print("DOMESTIC MINUS INTERNATIONAL ADMIT RATE (percentage points)")
print("-" * 58)
print(f"{'campus':<15}{str(START):>9}{str(END):>9}{'change':>10}")
for campus, first, last, change in results:
    print(f"{campus:<15}{first:>9.1f}{last:>9.1f}{change:>+10.1f}")

widened = sum(1 for r in results if r[3] > 0)
narrowed = sum(1 for r in results if r[3] < 0)
changes = sorted(r[3] for r in results)
median = changes[len(changes) // 2]
print("-" * 58)
print(f"Widened at {widened} campuses, narrowed at {narrowed}. "
      f"Median change {median:+.1f} points.")

# ---------------------------------------------------------------- every year
print()
print("THE GAP EVERY YEAR")
print("-" * 74)
print(f"{'campus':<15}" + "".join(f"{y:>8}" for y in YEARS))
for campus, _, _, _ in results:
    print(f"{campus:<15}" + "".join(f"{gap(campus, y):>8.1f}" for y in YEARS))

# ---------------------------------------------------------------- what moved
print()
print(f"THE RATES BEHIND IT ({START} to {END}, percent admitted)")
print("-" * 74)
print(f"{'campus':<15}{'dom ' + str(START):>10}{'dom ' + str(END):>10}"
      f"{'int ' + str(START):>10}{'int ' + str(END):>10}{'driver':>16}")
for campus, _, _, change in results:
    d0, i0 = rates(DATA[campus][START])
    d1, i1 = rates(DATA[campus][END])
    move_dom, move_int = d1 - d0, i1 - i0
    if abs(move_dom) >= 2 * abs(move_int):
        driver = "domestic moved"
    elif abs(move_int) >= 2 * abs(move_dom):
        driver = "intl moved"
    else:
        driver = "both moved"
    print(f"{campus:<15}{d0:>10.1f}{d1:>10.1f}{i0:>10.1f}{i1:>10.1f}{driver:>16}")

# ---------------------------------------------------------------- plain chart
print()
print("THE GAP OVER TIME  (| marks zero, each column is one year)")
print("-" * 74)
SCALE = 0.5  # characters per percentage point
WIDTH = 20   # characters on each side of zero
for campus, _, _, _ in results:
    print(f"\n{campus}")
    for year in YEARS:
        g = gap(campus, year)
        n = int(round(abs(g) * SCALE))
        n = min(n, WIDTH)
        if g >= 0:
            bar = " " * WIDTH + "|" + "#" * n
        else:
            bar = " " * (WIDTH - n) + "#" * n + "|"
        print(f"  {year}  {bar:<45}{g:+6.1f}")

print()
print("Above zero the domestic rate is higher; below zero the international")
print("rate is higher. 'Domestic' includes California residents and")
print("out-of-state Americans together, since the source file does not")
print("separate them.")
