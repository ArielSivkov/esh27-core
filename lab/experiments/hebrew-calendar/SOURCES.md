# מקורות — הלוח העברי ב-Lean (lab/lean/Hebrew)

כל טענה בקוד נושאת מקור (יסוד ב: בשם אומרו). להלן הטקסטים המדויקים שהוטמעו, עם ההפניה לשם ההגדרה/המשפט ב-Lean.

## 1. רמב"ם, משנה תורה, הלכות קידוש החודש פרקים ו–ח

- **מקור הטקסט העברי:** Sefaria, גרסת "Torat Emet 363" (Public Domain), API: `https://www.sefaria.org/api/v3/texts/Mishneh_Torah,_Sanctification_of_the_New_Month.<פרק>?version=hebrew` (נשלף 2026-11-07).
- **תרגום אנגלי:** Eliyahu Touger, Moznaim (via Sefaria, `?version=english`). ההערות של טוגר הושמטו.
- מספור ההלכות: כפי שמופיע ב-Sefaria (פרק:הלכה). מספור בדפוסים אחרים עשוי לסטות באחת.

### קידוש החודש 6:2  — ב-Lean: `partsPerHour, partsPerDay`

> הַיּוֹם וְהַלַּיְלָה אַרְבַּע וְעֶשְׂרִים שָׁעוֹת בְּכָל זְמַן. שְׁתֵּים עֶשְׂרֵה בַּיּוֹם וּשְׁתֵּים עֶשְׂרֵה בַּלַּיְלָה. וְהַשָּׁעָה מְחֻלֶּקֶת לְאֶלֶף וּשְׁמוֹנִים חֲלָקִים. וְלָמָּה חִלְּקוּ הַשָּׁעָה לְמִנְיָן זֶה. לְפִי שֶׁמִּנְיָן זֶה יֵשׁ בּוֹ חֲצִי וּרְבִיעַ וּשְׁמִינִית וּשְׁלִישׁ וּשְׁתוּת וְתֵשַׁע וְחֹמֶשׁ וְעִשּׂוּר. וְהַרְבֵּה חֲלָקִים יֵשׁ לְכָל אֵלּוּ הַשֵּׁמוֹת:

> *Day and night are constantly considered a twenty-four hour composite, [on the average:] twelve [hours] of daylight and twelve [hours] of night. An hour can be divided into 1080 units. This number was chosen because it can be divided in half, into fourths, eighths, thirds, sixths, ninths, and tenths. Each of these fractions contains many of these units.*

### קידוש החודש 6:3  — ב-Lean: `lunation`

> מִשֶּׁיִּתְקַבֵּץ הַיָּרֵחַ וְהַחַמָּה לְפִי חֶשְׁבּוֹן זֶה עַד שֶׁיִּתְקַבְּצוּ פַּעַם שְׁנִיָּה בְּמַהֲלָכָם הָאֶמְצָעִי. תִּשְׁעָה וְעֶשְׂרִים יוֹם וּשְׁתֵּים עֶשְׂרֵה שָׁעוֹת מִיּוֹם שְׁלֹשִׁים מִתְּחִלַּת לֵילוֹ. וּשְׁבַע מֵאוֹת וּשְׁלֹשָׁה וְתִשְׁעִים חֲלָקִים מִשְּׁעַת שְׁלֹשׁ עֶשְׂרֵה. וְזֶה הוּא הַזְּמַן שֶׁבֵּין כָּל מוֹלָד וּמוֹלָד וְזֶה הוּא חָדְשָׁהּ שֶׁל לְבָנָה:

> *According to this calculation, [the interval] between one conjunction of the moon and the sun and the subsequent conjunction according to their mean movement is twenty-nine full days, twelve hours of the thirtieth day, and 793 units of the thirteenth hour. This is the interval between one conjunction and the next, [and thus,] the length of a lunar month.*

### קידוש החודש 6:4  — ב-Lean: `twelve_lunations / thirteen_lunations`

> שָׁנָה שֶׁל לְבָנָה אִם תִּהְיֶה שְׁנֵים עָשָׂר חֹדֶשׁ מֵחֳדָשִׁים אֵלּוּ יִהְיֶה כְּלָלָהּ שְׁלֹשׁ מֵאוֹת יוֹם וְאַרְבָּעָה וַחֲמִשִּׁים יוֹם וּשְׁמוֹנֶה שָׁעוֹת וּשְׁמוֹנֶה מֵאוֹת וְשִׁשָּׁה וְשִׁבְעִים חֲלָקִים. וְאִם תִּהְיֶה מְעֻבֶּרֶת וְתִהְיֶה הַשָּׁנָה שְׁלֹשָׁה עָשָׂר חֹדֶשׁ יִהְיֶה כְּלָלָהּ שְׁלֹשׁ מֵאוֹת וּשְׁמוֹנִים וּשְׁלֹשָׁה יוֹם וְאַחַת וְעֶשְׂרִים שָׁעוֹת וַחֲמֵשׁ מֵאוֹת וְתִשְׁעָה וּשְׁמוֹנִים חֲלָקִים. וּשְׁנַת הַחַמָּה הִיא שְׁלֹשׁ מֵאוֹת חֲמִשָּׁה וְשִׁשִּׁים יוֹם וְשֵׁשׁ שָׁעוֹת. נִמְצָא תּוֹסֶפֶת שְׁנַת הַחַמָּה עַל שְׁנַת הַלְּבָנָה עֲשָׂרָה יָמִים וְאַחַת וְעֶשְׂרִים שָׁעוֹת וּמָאתַיִם וְאַרְבָּעָה חֲלָקִים:

> *[Accordingly,] an [ordinary] lunar year, which includes twelve of these months, would include three hundred fifty-four days, eight hours, and eight hundred seventy-six units.A leap year, which would include thirteen of these months, would include three hundred eighty-three days, twenty-one hours, and five hundred eighty-nine units.A solar year is three hundred sixty-five days and six hours. Thus, a solar year exceeds an [ordinary] lunar year by ten days, twenty-one hours, and two hundred and four units.*

### קידוש החודש 6:8  — ב-Lean: `baharad, molad_succ`

> וְכֵן כְּשֶׁיִּהְיֶה עִמְּךָ יָדוּעַ מוֹלַד שָׁנָה זוֹ וְתוֹסִיף שְׁאֵרִיתָהּ עַל יְמֵי הַמּוֹלָד. אִם פְּשׁוּטָה הִיא שְׁאֵרִית הַפְּשׁוּטָה וְאִם מְעֻבֶּרֶת הִיא שְׁאֵרִית הַמְעֻבֶּרֶת. יֵצֵא לְךָ מוֹלַד שָׁנָה שֶׁלְּאַחֲרֶיהָ. וְכֵן שָׁנָה אַחַר שָׁנָה עַד סוֹף הָעוֹלָם. וְהַמּוֹלָד הָרִאשׁוֹן שֶׁמִּמֶּנּוּ תַּתְחִיל הוּא מוֹלַד שֶׁהָיָה בַּשָּׁנָה הָרִאשׁוֹנָה שֶׁל יְצִירָה. וְהוּא הָיָה בְּלֵיל שֵׁנִי חָמֵשׁ שָׁעוֹת בַּלַּיְלָה וּמָאתַיִם וְאַרְבָּעָה חֲלָקִים. סִימָן לָהֶם בהר"ד וּמִמֶּנּוּ הוּא תְּחִלַּת הַחֶשְׁבּוֹן:

> *Similarly, if you know the time of the conjunction for a particular year and you add its remainder - either the remainder of an ordinary year or the remainder of a leap year - to the time of the conjunction, you will determine the time of the conjunction of the following year. This method [of calculation] may be followed year after year for eternity.The first conjunction from which we begin, the conjunction of the first year of creation, was on Monday night, 5 hours and 204 units after nightfall 8 a,b, explains that this follows the view of Rabbi Eliezer (Rosh HaShanah 10b), who states that the world was created in Tishrei. According to this conception, the conjunction for Rosh HaShanah, the day of Adam's creation, was the fourteenth hour of Friday (the second hour after sunrise). Since the first day of creation was the twenty-fifth of Elul, the year prior to that of Adam's creation is also significant. To calculate the conjunction of that year, we subtract the remainder of an ordinary year - 4 days, 8 hours, and 876 units - from six days and fourteen hours. This produces the figure cited by the Rambam. (in numerical terms, 2 - 5 - 204). This is the starting point for these calculations.*

### קידוש החודש 6:9  — ב-Lean: `weekday (mod 7), moladTime`

> בְּכָל הַחֶשְׁבּוֹנוֹת הָאֵלּוּ שֶׁתֵּדַע מֵהֶן הַמּוֹלָד. כְּשֶׁתּוֹסִיף שְׁאֵרִית עִם שְׁאֵרִית. כְּשֶׁיִּתְקַבֵּץ מִן הַחֲלָקִים אֶלֶף וּשְׁמוֹנִים תַּשְׁלִים שָׁעָה אַחַת וְתוֹסִיף אוֹתָהּ לְמִנְיַן הַשָּׁעוֹת. וּכְשֶׁיִּתְקַבֵּץ מִן הַשָּׁעוֹת אַרְבַּע וְעֶשְׂרִים תַּשְׁלִים יוֹם וְתוֹסִיף מִמֶּנּוּ לְמִנְיַן הַיָּמִים. וּכְשֶׁיִּתְקַבֵּץ מִן הַיָּמִים יוֹתֵר עַל שִׁבְעָה תַּשְׁלִיךְ שִׁבְעָה מִן הַמִּנְיָן וְתַנִּיחַ הַשְּׁאָר. שֶׁאֵין אָנוּ מְחַשְּׁבִין לֵידַע מִנְיַן הַיָּמִים אֶלָּא לֵידַע בְּאֵי זֶה יוֹם מִימֵי הַשָּׁבוּעַ וּבְאֵי זֶה שָׁעָה וְאֵי זֶה חֵלֶק יִהְיֶה הַמּוֹלָד:

> *In all the calculations to determine the time of the conjunction, when the remainder [of one period] should be added to another remainder, [the following principles should be adhered to:] When a sum of 1080 units is reached, it should be counted as an hour, and added to the number of the hours. When a sum of twenty-four hours is reached, it should be counted as a day, and added to the number of days. When the number of days is greater than seven, [all multiples of] seven should be subtracted from the sum, and the remainder be focused on.For the purpose of our calculations is not to know the number of days, but rather to know on which day of the week, and at what hour and after how many units will the conjunction take place.*

### קידוש החודש 6:10  — ב-Lean: `235 months per cycle (elapsedMonths)`

> כָּל תְּשַׁע עֶשְׂרֵה שָׁנָה שֶׁיִּהְיוּ מֵהֶן שֶׁבַע שָׁנִים מְעֵבָּרוֹת וּשְׁתֵּים עֶשְׂרֵה פְּשׁוּטוֹת נִקְרָא מַחֲזוֹר. וְלָמָּה סָמַכְנוּ עַל מִנְיָן זֶה. שֶׁבִּזְמַן שֶׁאַתָּה מְקַבֵּץ מִנְיַן יְמֵי שְׁתֵּים עֶשְׂרֵה שָׁנָה פְּשׁוּטוֹת וְשֶׁבַע מְעֵבָּרוֹת וּשְׁעוֹתֵיהֶן וְחֶלְקֵיהֶן וְתַשְׁלִים כָּל אֶלֶף וּשְׁמֹנִים חֲלָקִים שָׁעָה. וְכָל אַרְבַּע וְעֶשְׂרִים שָׁעוֹת יוֹם. וְתוֹסִיף לְמִנְיַן הַיָּמִים. תִּמְצָא הַכּל תְּשַׁע עֶשְׂרֵה שָׁנָה מִשְּׁנֵי הַחַמָּה שֶׁכָּל שָׁנָה מֵהֶן שְׁלֹשׁ מֵאוֹת וַחֲמִשָּׁה וְשִׁשִּׁים יוֹם וְשֵׁשׁ שָׁעוֹת בְּשָׁוֶה. וְלֹא יִשָּׁאֵר מִמִּנְיַן יְמֵי הַחַמָּה בְּכָל תְּשַׁע עֶשְׂרֵה שָׁנָה חוּץ מִשָּׁעָה אַחַת וְאַרְבַּע מֵאוֹת וּשְׁמוֹנִים וַחֲמִשָּׁה חֲלָקִים. סִימָן לָהֶם אתפ"ה:

> *[The fixed calendar is structured in] a nineteen-year cycle, including seven leap years and twelve ordinary years. This is called a machzor.Why was this [structure] chosen? Because when you total the number of days in twelve ordinary years and seven leap years together with their hours and their units, counting all [sums of] 1080 units as an hour, [all sums of] twenty-four hours as a day, and adding them to the number of days, the total will equal nineteen solar years, each of these years being 365 days and six hours.The difference between the days of the solar calendar [and the lunar calendar] will be only one hour and 485 units (in numerical terms, 1 - 485).*

### קידוש החודש 6:11  — ב-Lean: `leapCycleYear / isLeap`

> נִמְצָא בְּמַחֲזוֹר שֶׁהוּא כָּזֶה הֶחֳדָשִׁים כֻּלָּם חָדְשֵׁי הַלְּבָנָה וְהַשָּׁנִים שְׁנֵי הַחַמָּה. וְהַשֶּׁבַע שָׁנִים הַמְעֻבָּרוֹת שֶׁבְּכָל מַחֲזוֹר וּמַחֲזוֹר לְפִי חֶשְׁבּוֹן זֶה הֵם שָׁנָה שְׁלִישִׁית מִן הַמַּחֲזוֹר וְשִׁשִּׁית וּשְׁמִינִית וּשְׁנַת אַחַת עֶשְׂרֵה וּשְׁנַת אַרְבַּע עֶשְׂרֵה וּשְׁנַת שְׁבַע עֶשְׂרֵה וּשְׁנַת י"ט. סִימָן לָהֶם גו"ח י"א י"ד י"ז י"ט:

> *Thus, in such a [nineteen-year] cycle, the months are lunar months, and the years are solar years. The seven leap years in each cycle should be the following: The third year of the cycle, the sixth year, the eighth year, the eleventh year, the fourteenth year, the seventeenth year, the nineteenth year (in numbers, 3, 6, 8, 11, 14, 17, 19).*

### קידוש החודש 6:12  — ב-Lean: `cycle_remainder`

> כְּשֶׁתְּקַבֵּץ שְׁאֵרִית כָּל שָׁנָה מִשְּׁתֵּים עֶשְׂרֵה שָׁנָה הַפְּשׁוּטוֹת שֶׁהִיא ד"ח תתע"ו. וּשְׁאֵרִית כָּל שָׁנָה מִשֶּׁבַע שָׁנִים הַמְעֻבָּרוֹת שֶׁהִיא הכ"א תקפ"ט. וְתַשְׁלִיךְ הַכּל שִׁבְעָה שִׁבְעָה יִשָּׁאֵר שְׁנֵי יָמִים וְשֵׁשׁ עֶשְׂרֵה שָׁעוֹת וַחֲמֵשׁ מֵאוֹת וַחֲמִשָּׁה וְתִשְׁעִים חֲלָקִים. סִימָן לָהֶם בי"ו תקצ"ה. וְזֶה הוּא שְׁאֵרִית הַמַּחֲזוֹר:

> *When you add the remainders of each of the twelve ordinary years, [the remainder of each year] being 4 - 8 - 876, and the remainders of the seven leap years, [the remainder of each year] being 5 - 21 - 589, and then divide the entire sum in groups of seven, there is a remainder of two days, sixteen hours, and 595 units (in numerical terms, 2 - 16 - 595). This is the remainder of a [nineteen-year] cycle.*

### קידוש החודש 6:13  — ב-Lean: `baharad, molad (= molad Tishrei)`

> כְּשֶׁיִּהְיֶה לְךָ יָדוּעַ מוֹלַד תְּחִלַּת מַחֲזוֹר וְתוֹסִיף עָלָיו בי"ו תקצ"ה. יָצָא לְךָ תְּחִלַּת הַמַּחֲזוֹר שֶׁאַחֲרָיו וְכֵן מוֹלַד כָּל מַחֲזוֹר וּמַחֲזוֹר עַד סוֹף הָעוֹלָם. וּכְבָר אָמַרְנוּ שֶׁמּוֹלַד תְּחִלַּת הַמַּחֲזוֹר הָרִאשׁוֹן הָיָה לבהר"ד. וּמוֹלַד הַשָּׁנָה הוּא מוֹלַד תִּשְׁרֵי שֶׁל אוֹתָהּ הַשָּׁנָה:

> *When you know the time of the conjunction of the beginning of a [nineteen-year] cycle, by adding 2 - 16 - 595 to it you will be able to determine the beginning of the next [nineteen-year] cycle, and similarly all the [subsequent nineteen-year] cycles for eternity. As stated above, the conjunction [marking] the beginning of the first [nineteen-year] cycle took place on 2 - 5 - 204. [The expression,] the conjunction of a year refers to the conjunction of the month of Tishrei for that year.*

### קידוש החודש 6:14  — ב-Lean: `elapsedMonths, molad`

> וּבַדֶּרֶךְ הַזֹּאת תֵּדַע מוֹלַד כָּל שָׁנָה וְשָׁנָה שֶׁתִּרְצֶה. וּמוֹלַד כָּל חֹדֶשׁ וְחֹדֶשׁ שֶׁתִּרְצֶה. מִשָּׁנִים שֶׁעָבְרוּ אוֹ מִשָּׁנִים שֶׁעֲתִידִים לָבֹא. כֵּיצַד. תִּקַּח שְׁנֵי יְצִירָה שֶׁעָבְרוּ וְגָמְרוּ וְתַעֲשֶׂה אוֹתָם מַחֲזוֹרִין שֶׁל תְּשַׁע עֶשְׂרֵה תְּשַׁע עֶשְׂרֵה שָׁנָה עַד תִּשְׁרֵי שֶׁל אוֹתָהּ הַשָּׁנָה. וְתֵדַע מִנְיַן הַמַּחֲזוֹרִין שֶׁעָבְרוּ וּמִנְיַן הַשָּׁנִים שֶׁעָבְרוּ מִמַּחֲזוֹר שֶׁעֲדַיִן לֹא נִשְׁלַם. וְתִקַּח לְכָל מַחֲזוֹר וּמַחֲזוֹר בי"ו תקצ"ה. וּלְכָל שָׁנָה וְשָׁנָה פְּשׁוּטָה מִשְּׁנֵי הַמַּחֲזוֹר שֶׁלֹּא נִשְׁלַם ד"ח תתע"ו. וּלְכָל שָׁנָה מְעֵבֶּרֶת הכ"א תקפ"ט. וּתְקַבֵּץ הַכּל וְתַשְׁלִים הַחֲלָקִים שָׁעוֹת. וְתַשְׁלִים הַשָּׁעוֹת יָמִים. וְהַיָּמִים תַּשְׁלִיכֵם שִׁבְעָה שִׁבְעָה. וְהַנִּשְׁאָר מִן הַיָּמִים וּמִן הַשָּׁעוֹת וְהַחֲלָקִים הוּא מוֹלַד שָׁנָה הַבָּאָה שֶׁתִּרְצֶה לֵידַע מוֹלָדָהּ:

> *Using the above method, it is possible to know the conjunction [marking] the beginning of any particular year, or any particular month, whether for the years that have passed or for the years to come.What is implied? One should take the number of years that have passed until Tishrei of the [desired] year and group them in nineteen- year cycles. Thus, one will be able to determine the number of nineteen-year cycles that have passed and the number of years that have passed within the [nineteen-year] cycle that has not been completed [until the desired year]. One should add 2 - 16 - 595 for each cycle, 4 - 8 - 876 for every ordinary year of the cycle that has not been completed, and 5 - 21 - 589 for every leap year [of the cycle that has not been completed].One should then add together the entire sum, calculating [the groups of 1080] units as hours, the [groups of 24] hours as days, and the groups of seven days [as weeks]. [By adding] the remainder of the days, hours, and units [to 2 - 5 - 204], one can determine the time of the conjunction of the desired year.*

### קידוש החודש 7:1  — ב-Lean: `isADU, lo_adu`

> אֵין קוֹבְעִין לְעוֹלָם רֹאשׁ חֹדֶשׁ תִּשְׁרֵי לְפִי חֶשְׁבּוֹן זֶה לֹא בְּאֶחָד בְּשַׁבָּת וְלֹא בִּרְבִיעִי בְּשַׁבָּת וְלֹא בְּעֶרֶב שַׁבָּת. סִימָן לָהֶם אד"ו. אֶלָּא כְּשֶׁיִּהְיֶה מוֹלַד תִּשְׁרֵי בְּאֶחָד מִשְּׁלֹשָׁה יָמִים הָאֵלּוּ קוֹבְעִין רֹאשׁ חֹדֶשׁ בַּיּוֹם שֶׁלְּאַחֲרָיו. כֵּיצַד. הֲרֵי שֶׁהָיָה הַמּוֹלָד בְּאֶחָד בְּשַׁבָּת קוֹבְעִין רֹאשׁ חֹדֶשׁ תִּשְׁרֵי יוֹם שֵׁנִי. וְאִם הָיָה הַמּוֹלָד בִּרְבִיעִי קוֹבְעִין רֹאשׁ חֹדֶשׁ יוֹם חֲמִישִׁי. וְאִם הָיָה הַמּוֹלָד בְּשִׁשִּׁי קוֹבְעִין רֹאשׁ חֹדֶשׁ בִּשְׁבִיעִי:

> *[Rosh Chodesh is generally instituted on the day of the conjunction. Nevertheless,] Rosh Chodesh Tishrei should never be established on a Sunday, a Wednesday, or a Friday - in symbols, אד"ו - although, according to these calculations, [the conjunction for the month will occur on these days]. Instead, when the conjunction for the month of Tishrei occurs on any of these three days, Rosh Chodesh should be established on the following day.What is implied? When the conjunction occurs on Sunday, Rosh Chodesh Tishrei should be established on Monday. When the conjunction occurs on Wednesday, Rosh Chodesh Tishrei should be established on Thursday. When the conjunction occurs on Friday, Rosh Chodesh Tishrei should be established on the Sabbath.*

### קידוש החודש 7:2  — ב-Lean: `moladZaken`

> וְכֵן אִם יִהְיֶה הַמּוֹלָד בַּחֲצִי הַיּוֹם אוֹ לְמַעְלָה מֵחֲצִי הַיּוֹם קוֹבְעִין רֹאשׁ חֹדֶשׁ בַּיּוֹם שֶׁלְּאַחֲרָיו. כֵּיצַד. הֲרֵי שֶׁהָיָה הַמּוֹלָד בְּיוֹם שֵׁנִי בְּשֵׁשׁ שָׁעוֹת בַּיּוֹם אוֹ יֶתֶר עַל שֵׁשׁ שָׁעוֹת קוֹבְעִין רֹאשׁ חֹדֶשׁ בִּשְׁלִישִׁי. וְאִם יִהְיֶה הַמּוֹלָד קֹדֶם חֲצִי הַיּוֹם אֲפִלּוּ בְּחֵלֶק אֶחָד קוֹבְעִין רֹאשׁ הַחֹדֶשׁ בְּאוֹתוֹ יוֹם הַמּוֹלָד עַצְמוֹ. וְהוּא שֶׁלֹּא יִהְיֶה אוֹתוֹ הַיּוֹם מִימֵי אד"ו:

> *Similarly, if the conjunction [for the month of Tishrei] takes place at noon or after noon, Rosh Chodesh should be established on the following day., literally, "an aged conjunction." The rationale for postponing Rosh HaShanah in such a situation can be explained as follows: In principle, Rosh Chodesh is dependent on the sighting of the moon, not on the conjunction. As is explained in the subsequent chapters of the text, the new moon does not become visible until several hours after the conjunction between the moon and the sun. Thus, if the conjunction takes place after noon, it is impossible for the moon to be sighted on that day. Therefore, Rosh HaShanah is celebrated on the following day. (See Rosh HaShanah 20b and commentaries.)There is a slight difficulty in the Rambam's statements, for based on Chapter 15, Halachah 2, it would appear that at certain times it is possible to sight the moon only five hours after conjunction.What is implied? When the conjunction takes place on Monday, six hours after daybreak or later, Rosh Chodesh is established on Tuesday. If, however, the conjunction takes place before noon, even if only a single unit prior, Rosh Chodesh is established on the day of the conjunction, provided that day is neither Sunday, Wednesday, nor Friday.*

### קידוש החודש 7:3  — ב-Lean: `fixRH (ADU after zaken), fixRH_bounds`

> כְּשֶׁיִּהְיֶה הַמּוֹלָד בַּחֲצִי הַיּוֹם אוֹ אַחַר חֲצוֹת וְיִדָּחֶה לַיּוֹם שֶׁלְּאַחֲרָיו. אִם יִהְיֶה יוֹם שֶׁלְּאַחֲרָיו מִימֵי אד"ו הֲרֵי זֶה נִדְחֶה לְשֶׁלְּאַחֲרָיו וְיִהְיֶה רֹאשׁ הַחֹדֶשׁ קָבוּעַ בִּשְׁלִישִׁי מִיּוֹם הַמּוֹלָד. כֵּיצַד. הֲרֵי שֶׁיִּהְיֶה הַמּוֹלָד בְּשַׁבָּת בַּחֲצוֹת סִימָן זי"ח קוֹבְעִין רֹאשׁ הַחֹדֶשׁ בַּשָּׁנָה שֶׁמּוֹלָדָהּ כָּזֶה בְּשֵׁנִי בְּשַׁבָּת. וְכֵן אִם הָיָה הַמּוֹלָד בִּשְׁלִישִׁי בַּחֲצוֹת אוֹ אַחַר חֲצוֹת קוֹבְעִין רֹאשׁ הַחֹדֶשׁ בַּחֲמִישִׁי בְּשַׁבָּת:

> *When the conjunction takes place at noon or after noon, and [Rosh Chodesh Tishrei would be] postponed to the following day - if that following day is either Sunday, Wednesday, or Friday, Rosh Chodesh is postponed again, and is established on the third day after the conjunction.What is implied? If the conjunction takes place on the Sabbath after noon (in numbers, 7 - 18), in such a year Rosh Chodesh should be established on Monday.. Nor should it be established on Sunday, as stated in Halachah 1. Similarly, if the conjunction takes place on Tuesday at noon or after noon, Rosh Chodesh should be established on Thursday.*

### קידוש החודש 7:4  — ב-Lean: `gatrad`

> מוֹלַד תִּשְׁרֵי שֶׁיָּצָא בְּחֶשְׁבּוֹן זֶה בְּלֵיל שְׁלִישִׁי בְּתֵשַׁע שָׁעוֹת בַּלַּיְלָה וּמָאתַיִם וְאַרְבָּעָה חֲלָקִים מִשָּׁעָה עֲשִׂירִית סִימָנָהּ ג"ט ר"ד. אוֹ יוֹתֵר עַל זֶה. אִם הָיְתָה שָׁנָה פְּשׁוּטָה דּוֹחִין אֶת רֹאשׁ הַחֹדֶשׁ וְאֵין קוֹבְעִים אוֹתוֹ בִּשְׁלִישִׁי בְּשָׁנָה זוֹ אֶלָּא בַּחֲמִישִׁי בְּשַׁבָּת:

> *In an ordinary year, when the conjunction [of the month] of Tishrei falls on the night of the third day, nine hours and 204 units (in numbers, 3 - 9 - 204) or more after nightfall, Rosh Chodesh is postponed, and instead of being established on Tuesday, it is established on Thursday. 428).*

### קידוש החודש 7:5  — ב-Lean: `betutakpat`

> וְכֵן אִם יָצָא מוֹלַד תִּשְׁרֵי בְּיוֹם שֵׁנִי בְּשָׁלֹשׁ שָׁעוֹת בְּיוֹם וְתקפ"ט חֲלָקִים מִשָּׁעָה רְבִיעִית. סִימָנָהּ בט"ו תקפ"ט. אוֹ יֶתֶר עַל כֵּן. אִם הָיְתָה אוֹתָהּ הַשָּׁנָה מוֹצָאֵי הַמְעֻבֶּרֶת שֶׁהָיְתָה הַשָּׁנָה הַסְּמוּכָה לָהּ שֶׁעָבְרָה מְעֻבֶּרֶת. אֵין קוֹבְעִין רֹאשׁ הַחֹדֶשׁ בְּשֵׁנִי בְּשָׁנָה זוֹ אֶלָּא בִּשְׁלִישִׁי:

> *A similar situation [may arise] in a year that follows a leap year: If the conjunction for Tishrei takes place on Monday, three hours and 589 units or more after daybreak (in numbers, 2 - 15 - 589), Rosh Chodesh is not established on Monday, but on Tuesday. 428).*

### קידוש החודש 7:6  — ב-Lean: `fixRH, roshHashanah`

> הָיָה מוֹלַד הַשָּׁנָה הַפְּשׁוּטָה שֶׁאָמַרְנוּ שֶׁתִּדָּחֶה לַחֲמִישִׁי פָּחוֹת חֵלֶק אֶחָד. כְּגוֹן שֶׁיָּצָא סִימָנָהּ ג"ט ר"ג אוֹ פָּחוֹת מִזֶּה. קוֹבְעִין אוֹתָהּ בִּשְׁלִישִׁי. וְכֵן אִם הָיָה מוֹלַד מוֹצָאֵי הָעִבּוּר בְּיוֹם שֵׁנִי פָּחוֹת חֵלֶק. כְּגוֹן שֶׁהָיָה סִימָנָהּ בט"ו תקפ"ח אוֹ פָּחוֹת מִזֶּה. קוֹבְעִין אוֹתָהּ בְּשֵׁנִי. נִמְצָא דֶּרֶךְ קְבִיעַת רֹאשׁ חֹדֶשׁ תִּשְׁרֵי לְפִי חֶשְׁבּוֹן זֶה כָּךְ הוּא. תַּחְשֹׁב וְתֵדַע הַמּוֹלָד בְּאֵי זֶה יוֹם יִהְיֶה וּבְכַמָּה שָׁעוֹת מִן הַיּוֹם אוֹ מִן הַלַּיְלָה וּבְכַמָּה חֲלָקִים מִן הַשָּׁעָה. וְיוֹם הַמּוֹלָד הוּא יוֹם הַקְּבִיעָה לְעוֹלָם. אֶלָּא אִם כֵּן הָיָה בְּאֶחָד בְּשַׁבָּת אוֹ בִּרְבִיעִי אוֹ בְּעֶרֶב שַׁבָּת. אוֹ אִם הָיָה הַמּוֹלָד בַּחֲצוֹת הַיּוֹם אוֹ אַחַר חֲצוֹת. אוֹ אִם הָיָה בר"ד חֲלָקִים מִשָּׁעָה עֲשִׂירִית מִלֵּיל שְׁלִישִׁי אוֹ יוֹתֵר עַל זֶה וְהָיְתָה שָׁנָה פְּשׁוּטָה. אוֹ שֶׁהָיָה הַמּוֹלָד בתקפ"ט חֲלָקִים מִשָּׁעָה רְבִיעִית מִיּוֹם שֵׁנִי וְהָיְתָה הַשָּׁנָה פְּשׁוּטָה שֶׁאַחַר הַמְעֵבֶּרֶת. שֶׁאִם יֶאֱרַע בְּאֶחָד מֵאַרְבָּעָה דְּבָרִים הָאֵלּוּ אֵין קוֹבְעִין בְּיוֹם הַמּוֹלָד אֶלָּא בַּיּוֹם שֶׁלְּאַחֲרָיו אוֹ שֶׁלְּאַחַר אַחֲרָיו כַּדֶּרֶךְ שֶׁבֵּאַרְנוּ:

> *If, however, the conjunction of an ordinary year occurs [even] one unit earlier - i.e., were it to be 3 - 9 - 203 or earlier - [Rosh Chodesh] should be established on Tuesday, [rather than postponed until Thursday as mentioned above].Similarly, if the conjunction of a year following a leap year occurs [even] one unit earlier - i.e., were it to be 2 - 15 - 588 or earlier - [Rosh Chodesh] should be established on Monday.Thus, the way to determine [the day on which] Rosh Chodesh Tishrei will be established according to these calculations is as follows: One should first determine the day [of the week], the hour of the day - or night - and the number of units of the hour when the conjunction takes place. The day of the conjunction will be the day of Rosh Chodesh, except in the following instances:a) [The conjunction] takes place on Sunday, Wednesday, or Friday;b) The conjunction takes place at noon or after noon;c) In an ordinary year, [the conjunction] takes place on the night of the third day, after 204 units of the tenth hour have passed, or later [that day];d) In an ordinary year that follows a leap year, the conjunction takes place on Monday past 589 units of the fourth hour after daybreak has passed or later [that day].If the conjunction occurs in one of these four instances, [Rosh Chodesh] is not established on the day of the conjunction, but rather on the day that follows, or on the day following that, as explained.*

### קידוש החודש 7:7  — ב-Lean: `rh_weekday (background)`

> וּמִפְּנֵי מָה אֵין קוֹבְעִין בְּחֶשְׁבּוֹן זֶה בִּימֵי אד"ו. לְפִי שֶׁהַחֶשְׁבּוֹן הַזֶּה הוּא לְקִבּוּץ הַיָּרֵחַ וְהַשֶּׁמֶשׁ בְּהִלּוּכָהּ הָאֶמְצָעִי לֹא בַּמָּקוֹם הָאֲמִתִּי כְּמוֹ שֶׁהוֹדַעְנוּ. לְפִיכָךְ עָשׂוּ יוֹם קְבִיעָה וְיוֹם דְּחִיָּה כְּדֵי לִפְגֹּעַ בְּיוֹם קִבּוּץ הָאֲמִתִּי. כֵּיצַד. בִּשְׁלִישִׁי קוֹבְעִין בִּרְבִיעִי דּוֹחִין. בַּחֲמִישִׁי קוֹבְעִין בְּשִׁשִּׁי דּוֹחִין. בְּשַׁבָּת קוֹבְעִין אֶחָד בְּשַׁבָּת דּוֹחִין. בְּשֵׁנִי קוֹבְעִין:

> *Why is [Rosh HaShanah] not established [on the day of the conjunction] when it falls on Sunday, Wednesday, or Friday? Because these calculations determine the conjunction of the sun and the moon only according to their mean [rate of] progress, and do not [necessarily] reflect the true position [of the sun and the moon in the celestial sphere], as explained. Therefore, they instituted that [on] one day [Rosh Chodesh] would be established and on the following day it would be postponed, so that they would ascertain the day when the true conjunction takes place. 20a why Rosh HaShanah never begins on these days. The Talmud states that if Rosh HaShanah falls on either Wednesday or Friday, Yom Kippur will fall on either Friday or Sunday, and thus there would be two consecutive days, Yom Kippur and the Sabbath, when it would be forbidden to bury the dead. In the Talmudic era, this could have caused a corpse to deteriorate, detracting from its honor and respect.Alternatively, the Sages state that if Rosh HaShanah fell on any of these three days, there would be two successive days when it would be forbidden to pick fresh vegetables, and the people would be unable to celebrate the festivals or the Sabbath properly.Sukkah 43a gives another reason why Rosh HaShanah is not held on Sunday: were this to be the case, Hoshana Rabbah, the seventh day of Sukkot, would fall on the Sabbath. In such an instance, restrictions were placed on the willow ritual in the Temple. (See Hilchot Shofar, Sukkah V'Lulav 7:21-22.) To avoid such an instance, the Sages structured the calendar so that Rosh HaShanah never falls on Sunday.In defense of the Rambam's position, it must be noted that both earlier (Rabbenu Chanan'el) and subsequent (the P'nei Yehoshua) Talmudic commentaries understood the reasons given by the Talmud as being merely the external dimension of the rationale for the calendar's adjustment, while the inner meaning is associated with the actual position of the sun and the moon in the heavenly sphere.Even according to this perspective, there is, however, a difficulty with the Rambam's statements. Although it is correct that the true positions of the sun and the moon often differ from the position determined by calculating their mean movement, the concept of postponing the celebration of Rosh HaShanah on these three days appears arbitrary and without any obvious connection to the movement of these bodies in the celestial sphere. The commentaries note that explanations why Rosh HaShanah is not celebrated on these days are found in the Kabbalah.What is implied? [When according to our calculations, the conjunction occurs on] Tuesday, we establish [Rosh Chodesh]. [When it occurs] on Wednesday, we postpone it. [When it occurs] on Thursday, we establish [Rosh Chodesh]. [When it occurs] on Friday, we postpone it. [When it occurs] on the Sabbath, we establish [Rosh Chodesh]. [When it occurs] on Sunday, we postpone it. [When it occurs] on Monday, we establish [Rosh Chodesh].*

### קידוש החודש 8:1  — ב-Lean: `(background: whole days)`

> חָדְשָׁה שֶׁל לְבָנָה תִּשְׁעָה וְעֶשְׂרִים יוֹם וּמֶחֱצָה וְתשצ"ג חֲלָקִים כְּמוֹ שֶׁבֵּאַרְנוּ. וְאִי אֶפְשָׁר לוֹמַר שֶׁרֹאשׁ הַחֹדֶשׁ יִהְיֶה בְּמִקְצָת הַיּוֹם עַד שֶׁיִּהְיֶה מִקְצָת הַיּוֹם מֵחֹדֶשׁ שֶׁעָבַר וּמִקְצָתוֹ מֵהַבָּא. שֶׁנֶּאֱמַר (במדבר יא כ) "עַד חֹדֶשׁ יָמִים" מִפִּי הַשְּׁמוּעָה לָמְדוּ שֶׁיָּמִים אַתָּה מְחַשֵּׁב לְחֹדֶשׁ וְאִי אַתָּה מְחַשֵּׁב שָׁעוֹת:

> *A lunar month is twenty-nine and one half days, and 793 units, as we have explained. It is impossible for Rosh Chodesh to begin in the middle of the day - i.e., that a portion of the day would be part of the previous month and a portion of the day would be part of the following month - as [implied by Numbers 11:20]: "For a month of days...." According to the Oral Tradition, 5a. this was interpreted [to mean], "You count the days of a month; you do not count the hours [of a month]."*

### קידוש החודש 8:2  — ב-Lean: `(background)`

> לְפִיכָךְ עוֹשִׂין חָדְשֵׁי הַלְּבָנָה מֵהֶן חֹדֶשׁ חָסֵר וּמֵהֶם חֹדֶשׁ מָלֵא. חֹדֶשׁ חָסֵר תִּשְׁעָה וְעֶשְׂרִים יוֹם בִּלְבַד וְאַף עַל פִּי שֶׁחָדְשָׁהּ שֶׁל לְבָנָה יֶתֶר עַל זֶה בְּשָׁעוֹת. וְחֹדֶשׁ מָלֵא מִשְּׁלֹשִׁים יוֹם וְאַף עַל פִּי שֶׁחָדְשָׁהּ שֶׁל לְבָנָה פָּחוֹת מִזֶּה בְּשָׁעוֹת. כְּדֵי שֶׁלֹּא לְחַשֵּׁב שָׁעוֹת בַּחֹדֶשׁ אֶלָּא יָמִים שְׁלֵמִים:

> *Therefore, some lunar months are established as lacking [a day], and others as full. A month that is lacking has only twenty- nine days, even though a lunar month is several hours longer. A full month is thirty days, even though a lunar month is several hours shorter. In this manner, the months will be calculated according to complete days, not according to hours.*

### קידוש החודש 8:4  — ב-Lean: `(background)`

> יוֹם שְׁלֹשִׁים לְעוֹלָם עוֹשִׂין אוֹתוֹ רֹאשׁ חֹדֶשׁ בְּחֶשְׁבּוֹן זֶה. אִם הָיָה הַחֹדֶשׁ שֶׁעָבַר חָסֵר יִהְיֶה יוֹם שְׁלֹשִׁים רֹאשׁ חֹדֶשׁ הַבָּא. וְאִם יִהְיֶה הַחֹדֶשׁ שֶׁעָבַר מָלֵא יִהְיֶה יוֹם שְׁלֹשִׁים רֹאשׁ חֹדֶשׁ הוֹאִיל וּמִקְצָתוֹ רֹאשׁ חֹדֶשׁ. וְיִהְיֶה תַּשְׁלוּם הַחֹדֶשׁ הַמָּלֵא שֶׁעָבַר. וְיִהְיֶה יוֹם אֶחָד וּשְׁלֹשִׁים רֹאשׁ הַחֹדֶשׁ הַבָּא וּמִמֶּנּוּ הוּא הַמִּנְיָן. וְהוּא יוֹם הַקְּבִיעָה. וּלְפִיכָךְ עוֹשִׂין רָאשֵׁי חֳדָשִׁים בְּחֶשְׁבּוֹן זֶה חֹדֶשׁ אֶחָד יוֹם אֶחָד בִּלְבַד וְחֹדֶשׁ אֶחָד שְׁנֵי יָמִים:

> *According to this reckoning, the thirtieth day of the month is always established as Rosh Chodesh. If the month is lacking, the thirtieth day will be Rosh Chodesh of the coming month.If the month is full [the coming month will have two days that are Rosh Chodesh]. The thirtieth day will be Rosh Chodesh, since a portion of it is [fit to be] Rosh Chodesh. [Nevertheless,] it will be counted as the completion of the previous month, which was full. The thirty-first day also will be Rosh Chodesh, and the reckoning [of the days of the coming month] will start from it. It is the day established [as Rosh Chodesh].Thus, according to this calculation, there are some months that have only one day Rosh Chodesh, and other months that have two days Rosh Chodesh.*

### קידוש החודש 8:5  — ב-Lean: `(background: fixed months)`

> סֵדֶר הֶחֳדָשִׁים הַמְּלֵאִים וְהַחֲסֵרִים לְפִי חֶשְׁבּוֹן זֶה כָּךְ הוּא. תִּשְׁרֵי לְעוֹלָם מָלֵא. וְטֵבֵת לְעוֹלָם חָסֵר. וּמִטֵּבֵת וְאֵילָךְ אֶחָד מָלֵא וְאֶחָד חָסֵר עַל הַסֵּדֶר. כֵּיצַד. טֵבֵת חָסֵר שְׁבָט מָלֵא. אֲדָר חָסֵר נִיסָן מָלֵא. אִיָּר חָסֵר סִיוָן מָלֵא. תַּמּוּז חָסֵר אָב מָלֵא. אֱלוּל חָסֵר. וּבְשָׁנָה הַמְעֻבֶּרֶת אֲדָר רִאשׁוֹן מָלֵא וַאֲדָר שֵׁנִי חָסֵר:

> *The following is the order of the full and lacking months according to [our] fixed calendar: Tishrei is always full. Tevet is always lacking. From Tevet on, there is one full month and one lacking month in sequence.What is implied? Tevet is lacking; Shevat is full; Adar is lacking; Nisan is full; Iyar, lacking; Sivan, full; Tammuz, lacking; Av, full; Elul, lacking. In a leap year, the first Adar is full, and the second Adar is lacking.*

### קידוש החודש 8:6  — ב-Lean: `yearKind (חסרה/כסדרה/שלמה)`

> נִשְׁאֲרוּ שְׁנֵי הֶחֳדָשִׁים שֶׁהֵן מַרְחֶשְׁוָן וְכִסְלֵו. פְּעָמִים יִהְיוּ שְׁנֵיהֶם מְלֵאִים וּפְעָמִים יִהְיוּ שְׁנֵיהֶם חֲסֵרִים וּפְעָמִים יִהְיֶה מַרְחֶשְׁוָן חָסֵר וְכִסְלֵו מָלֵא. וְשָׁנָה שֶׁיִּהְיוּ בָּהּ שְׁנֵי חֳדָשִׁים אֵלּוּ מְלֵאִים הִיא שֶׁנִּקְרְאוּ חֳדָשֶׁיהָ שְׁלֵמִים. וְשָׁנָה שֶׁיִּהְיוּ בָּהּ שְׁנֵי חֳדָשִׁים אֵלּוּ חֲסֵרִים נִקְרְאוּ חֳדָשֶׁיהָ חֲסֵרִין. וְשָׁנָה שֶׁיִּהְיוּ בָּהּ מַרְחֶשְׁוָן חָסֵר וְכִסְלֵו מָלֵא נִקְרְאוּ חֳדָשֶׁיהָ כְּסִדְרָן:

> *Two months remain: Marcheshvan and Kislev. Sometimes they are [both] full; sometimes they are [both] lacking; and sometimes Marcheshvan is lacking and Kislev is full.A year in which both of these months are full is called a year of complete months. A year in which both these months are lacking is called a year of lacking months. And a year in which Marcheshvan is lacking and Kislev is full is called a year whose months [proceed] in order.*

### קידוש החודש 8:7  — ב-Lean: `yearLength, yearKind`

> דֶּרֶךְ יְדִיעַת הַשָּׁנָה אִם חֳדָשֶׁיהָ מְלֵאִים אוֹ חֲסֵרִין אוֹ כְּסִדְרָן לְפִי חֶשְׁבּוֹן זֶה כָּךְ הוּא. תֵּדַע תְּחִלָּה יוֹם שֶׁנִּקְבַּע בּוֹ רֹאשׁ הַשָּׁנָה שֶׁתִּרְצֶה לֵידַע סִדּוּר חֳדָשֶׁיהָ כְּמוֹ שֶׁבֵּאַרְנוּ בְּפֶרֶק שְׁבִיעִי. וְתֵדַע יוֹם שֶׁיִּקָּבַע בּוֹ רֹאשׁ הַשָּׁנָה שֶׁלְּאַחֲרֶיהָ. וּתְחַשֵּׁב מִנְיַן הַיָּמִים שֶׁבֵּינֵיהֶן חוּץ מִיּוֹם הַקְּבִיעָה שֶׁל זוֹ וְשֶׁל זוֹ. אִם תִּמְצָא בֵּינֵיהֶן שְׁנֵי יָמִים יִהְיוּ חָדְשֵׁי הַשָּׁנָה חֲסֵרִין. וְאִם תִּמְצָא בֵּינֵיהֶם שְׁלֹשָׁה יָמִים יִהְיוּ כְּסִדְרָן. וְאִם תִּמְצָא בֵּינֵיהֶם אַרְבָּעָה יָמִים יִהְיוּ חָדְשֵׁי הַשָּׁנָה שְׁלֵמִים:

> *The way to know whether the months of a year will be lacking, will be complete, or will [proceed] in order [can be explained] as follows: First, determine the day on which Rosh HaShanah will fall in the year about whose months you desire to know, as explained in Chapter 7. Then determine the day on which Rosh HaShanah will fall in the year that follows.Afterwards, count the number of days between them without including the day on which Rosh HaShanah falls in either of these years. If there are only two days between them, the months of the year will be lacking. If there are three days between them, the months of the year will proceed in order. And if there are four days between them, the months of the year will be complete.*

### קידוש החודש 8:8  — ב-Lean: `yearLength_legal (leap)`

> בַּמֶּה דְּבָרִים אֲמוּרִים כְּשֶׁהָיְתָה הַשָּׁנָה שֶׁתִּרְצֶה לֵידַע סִדּוּר חֳדָשֶׁיהָ פְּשׁוּטָה. אֲבָל אִם הָיְתָה מְעֵבֶּרֶת. אִם תִּמְצָא בֵּין יוֹם קְבִיעָתָהּ וּבֵין יוֹם קְבִיעַת שָׁנָה שֶׁלְּאַחֲרֶיהָ אַרְבָּעָה יָמִים יִהְיוּ חָדְשֵׁי אוֹתָהּ שָׁנָה הַמְעֻבֶּרֶת חֲסֵרִים. וְאִם תִּמְצָא בֵּינֵיהֶם חֲמִשָּׁה יָמִים יִהְיוּ כְּסִדְרָן. וְאִם תִּמְצָא בֵּינֵיהֶם שִׁשָּׁה יִהְיוּ שְׁלֵמִים:

> *When does the above apply? When the year in question is an ordinary year. When, however, [the year in question] is a leap year [different rules apply]: If there are only four days between the day on which [Rosh HaShanah] is established [in the leap year] and the day on which it will be established in the following year, the months of the year will be lacking. If there are five days between these [two days], the months of the year will proceed in order. And if there are six days between them, the months of the year will be complete.*

### קידוש החודש 8:10  — ב-Lean: `rambam_8_10`

> יֵשׁ שָׁם סִימָנִין שֶׁתִּסְמֹךְ עֲלֵיהֶם כְּדֵי שֶׁלֹּא תִּטְעֶה בְּחֶשְׁבּוֹן סִדּוּר חָדְשֵׁי הַשָּׁנָה וְהֵן בְּנוּיִין עַל עִקְּרֵי זֶה הַחֶשְׁבּוֹן וְהַקְּבִיעוֹת וְהַדְּחִיּוֹת שֶׁבֵּאַרְנוּ דַּרְכָּם. וְאֵלּוּ הֵן. כָּל שָׁנָה שֶׁיִּהְיֶה רֹאשׁ הַשָּׁנָה בָּהּ בַּשְּׁלִישִׁי תִּהְיֶה לְעוֹלָם כְּסִדְרָן לְפִי חֶשְׁבּוֹן זֶה. בֵּין פְּשׁוּטָה בֵּין מְעֻבֶּרֶת. וְאִם יִהְיֶה רֹאשׁ הַשָּׁנָה בְּשַׁבָּת אוֹ בְּשֵׁנִי לֹא תִּהְיֶה כְּסִדְרָן לְעוֹלָם בֵּין בִּפְשׁוּטָה בֵּין בִּמְעֵבֶּרֶת. וְאִם יִהְיֶה רֹאשׁ הַשָּׁנָה בַּחֲמִישִׁי. אִם פְּשׁוּטָה הִיא אִי אֶפְשָׁר שֶׁיִּהְיוּ חֳדָשֶׁיהָ חֲסֵרִים לְפִי חֶשְׁבּוֹן זֶה. וְאִם מְעֻבֶּרֶת הִיא אִי אֶפְשָׁר שֶׁיִּהְיוּ חֳדָשֶׁיהָ כְּסִדְרָן לְפִי חֶשְׁבּוֹן זֶה:

> *There are certain indications upon which one can rely, so that one will not err regarding the calculation of the order of the months of a year. These principles are based on the fundamental principles of the fixed calendar and the determination of the days on which Rosh HaShanah will be established and those that will cause it to be postponed, as we explained previously.Whenever Rosh HaShanah is celebrated on a Tuesday, [the months of] the year will [proceed] in order. [This applies regardless of whether the year] is an ordinary year or a leap year.Whenever Rosh HaShanah is celebrated on the Sabbath or on a Monday, [the months of] the year will never [proceed] in order. [This applies regardless of whether the year] is an ordinary year or a leap year.[The following rules apply when] Rosh HaShanah falls on a Thursday. If the year is an ordinary year, it is impossible for its months to be lacking. If it is a leap year, it is impossible for its months to proceed in order.*

## 2. Russinoff, "Properties of the Hebrew Calendar" (ACL2)

- David M. Russinoff, *Properties of the Hebrew Calendar*, Proceedings ACL2 Workshop 2022, EPTCS 359, pp. 48–60. doi:10.4204/EPTCS.359.6. arXiv:2205.13345 (נשלף מ-arxiv.org 2026-11-07, PDF v1).
- קוד: `books/workshops/2022/russinoff-calendar/` בספריית ACL2 (`calendar.cpp`, `calendar.lisp`, `proof.lisp`). **[לא אומת]** — לא פתחנו את ה-repo של ACL2 (אין גישת רשת ל-github מהסשן הזה); הציטוטים להלן מן המאמר בלבד.
- מה שמוכח שם (סעיף 5 במאמר, ציטוט מילולי של שמות המשפטים):
  - `legal-year-lengths`: `(member (yearlength year) (if1 (leap year) '(383 384 385) '(353 354 355)))` — שתי הוכחות: #1 דרך המחזור m = 689472 (וחישוב של כל m השנים, 4 שניות), #2 ניתוח מקרים.
  - `keviyot`: אם ר"ה בג' → אורך ∈ {354,384}; בשבת או ב' → ∈ {353,355,383,385}; בה' → ∈ {354,355,383,385} ("לכל היותר 14").
  - `landau-thm`: המולד של כל חודש לפני סוף יום א' של החודש.
  - `molad-loop-decomp`, `molad-next`: נוסחת הנסיגה למולד.
- הערה מן המאמר (עמ' 56): "We seek the smallest number n of cycles that comprise an integral number of weeks … n = 2^6·3^4·7 = 36288" — זו מינימליות של **מחזור המולד מודולו שבוע**, לא של סדרת הקביעות; המאמר מוכיח רק ש-689472 **הוא** מחזור של אורכי השנים.
- לא אד"ו: לא מופיע כמשפט נפרד במאמר (הוא נובע מבנייה; `dayofweek-roshhashanah` מוזכר בדו"ח החדשנות שלנו כ-[לא אומת] מול ה-proof script).

## 3. ויקיפדיה (אנגלית), "Hebrew calendar" (raw wikitext, נשלף 2026-11-07)

> "The greatest common divisor of this and a week is 5 parts, so the Jewish calendar repeats exactly following a number of Metonic cycles equal to the number of parts in a week divided by 5, namely 7×24×216 = 36,288 Metonic cycles, or 689,472 Jewish years."

(שימו לב: הטיעון שם הוא על המולד; "repeats exactly" של הקביעות אינו מוכח שם, ומינימליות המחזור לסדרת הקביעות לא נטענת.)

## 4. Dershowitz & Reingold

- Nachum Dershowitz, Edward M. Reingold, *Calendrical Calculations*, Cambridge Univ. Press (מהדורות 1997–2018). הנוסחאות `hebrew-calendar-elapsed-days` ו-`hebrew-new-year-delay` — כפי שמומשו ב-`lab/experiments/novelty/sanity/hebrew_period.py` (האורקל שלנו). **[לא אומת מול הספר עצמו]**: הספר לא נגיש מהסשן; ההשוואה היא לקוד הפייתון בלבד.

## 5. Isabelle AFP / Coq

- `isa-afp.org` החזיר 403 דרך ה-proxy (2026-11-07) — **לא אומת** שאין פורמליזציה ב-AFP. דו"ח החדשנות (`lab/experiments/novelty/REPORT.md`) קבע "לא נמצא" על סמך חיפושים קודמים.

## 6. קבצים שלנו

- `lab/lean/Hebrew/Hebrew/Basic.lean` — הגדרות (עם ציטוטי ההלכות ב-docstrings).
- `lab/lean/Hebrew/Hebrew/Theorems.lean` — המשפטים.
- `lab/lean/Hebrew/Hebrew/DR.lean` — שקילות לניסוח דרשוביץ–ריינגולד.
- `lab/lean/Hebrew/Hebrew/CrossCheck.lean`, `Oracle.lean` — בדיקת הצלבה (`#guard`) מול `hebrew_period.py` לשנים 1..10001, נוצר ע"י `lab/experiments/hebrew-calendar/gen_oracle.py`.
