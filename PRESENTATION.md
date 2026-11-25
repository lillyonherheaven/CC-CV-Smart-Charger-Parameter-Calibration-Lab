# Slide-by-slide presentation guide — دليل العرض بالعربية والإنجليزية

**Project:** CC/CV Smart Charger & Parameter Calibration Lab — Math 3, Project 3.

**Timing:** 10–12 minutes including a short live demo. This is a speaker guide, not a fabricated experimental result or a slide deck file. Prepare slides using the listed equations and exported figures. All supplied bench data are synthetic; identify real measurements separately if collected.

**الهدف:** نشرح المعادلة التفاضلية، ثم نقارن طرق الحل، ثم نوضح كيف نقدر معاملات النموذج من البيانات. البيانات الموجودة في المشروع مُولَّدة بالمحاكاة وليست قياسات فعلية لبطارية.

## Slide 1 — Problem and contribution | المشكلة وفكرة المشروع

**Show:** title and the pipeline: physical model → exact solution → numerical methods → calibration → residuals → ZIP export.

**Say in English:** “We study battery charging as a first-order differential equation. Our contribution is an interactive CC/CV laboratory that separates numerical error, switching error, and model-to-data disagreement.”

**ملاحظات الشرح بالعربية:** «بدل ما نرسم منحنى شحن واحد، بنينا معملًا تفاعليًا. نغيّر المعاملات ونقارن طرق الحل، ثم نطابق النموذج مع البيانات. مهم نفرّق بين خطأ طريقة الحل وبين قصور النموذج نفسه.»

**Terms:** model = simplified mathematical description / نموذج رياضي مبسط؛ calibration = estimating parameters from data / تقدير معاملات النموذج من البيانات.

## Slide 2 — Circuit and state | الدائرة ومتغير الحالة

**Show:** an OCV source in series with internal resistance, and

$$
\dot s=\frac{\eta I}{3600Q_{Ah}},\qquad V_{term}=U(s)+RI,\qquad U(s)=a+bs.
$$

**Say:** “SoC is the state variable. Current increases stored charge. Capacity is entered in ampere-hours, so 3600 converts hours to seconds. Terminal voltage includes the internal-resistance drop during charging.”

**بالعربية:** «حالة الشحن، أو SoC، هي نسبة الشحنة المخزنة للسعة الكلية. نستخدم كسرًا بين صفر وواحد، وليس نسبة مئوية في الحسابات. بما أن الزمن بالثواني والسعة بالأمبير ساعة، نقسم على 3600. جهد الأطراف أثناء الشحن أكبر من جهد الدائرة المفتوحة بمقدار IR.»

**Terms:** State of Charge (SoC) / حالة الشحن؛ Open-Circuit Voltage (OCV) / جهد الدائرة المفتوحة؛ internal resistance / المقاومة الداخلية؛ terminal voltage / جهد الأطراف.

## Slide 3 — CC then CV | من التيار الثابت إلى الجهد الثابت

**Show:** `outputs/charging_curves.png`; point at the voltage plateau and current taper.

$$
s_{sw}=\frac{V_{max}-a-RI_{CC}}{b},\qquad
t_{sw}=\frac{s_{sw}-s_0}{r}\quad(s_0<s_{sw}).
$$

**Say:** “CC holds current constant while voltage rises. CV begins when terminal voltage reaches its limit; current then tapers. This crossover is different from termination, which occurs at a low current threshold.”

**بالعربية:** «في CC التيار ثابت، ولذلك حالة الشحن تزيد خطيًا. عندما يصل جهد الأطراف إلى الحد المحدد، ننتقل إلى CV: الجهد ثابت والتيار يقل تدريجيًا. الوصول إلى حد الجهد ليس نهاية الشحن؛ الإيقاف له شرط منفصل يعتمد على انخفاض التيار.»

**Terms:** Constant Current (CC) / تيار ثابت؛ Constant Voltage (CV) / جهد ثابت؛ crossover / لحظة الانتقال؛ termination / إنهاء الشحن.

## Slide 4 — Exact solution and equilibrium | الحل التحليلي ونقطة الاتزان

**Show:**

$$
s(t)=s_0+rt\quad\text{in CC},\qquad
s(t)=s_\infty-(s_\infty-s_c)e^{-(t-t_{sw})/\tau}\quad\text{in CV}.
$$

$$
\tau=\frac{3600Q_{Ah}R}{\eta b},\qquad s_\infty=\frac{V_{max}-a}{b}.
$$

**Say:** “The CV solution approaches equilibrium exponentially. In this ideal model, reaching the asymptotic full state exactly takes infinite time; practical charging ends at a finite current cutoff. Our phase line shows attraction from below.”

**بالعربية:** «الثابت الزمني تاو يحدد سرعة الاقتراب من الاتزان. الوصول الدقيق إلى الحد النهائي في الحل الأُسّي يحتاج زمنًا غير منتهٍ، لكن عمليًا نوقف عند تيار صغير محدد. الشاحن الذي يسمح بالشحن فقط لا يستطيع سحب شحنة لو بدأنا فوق نقطة الاتزان.»

**Show if asked:** `outputs/phase_line.png`. Its right-side arrows describe a mathematical bidirectional extension, not a charge-only device.

**Terms:** equilibrium / اتزان؛ stability / استقرار؛ time constant / ثابت زمني؛ asymptotic / اقتراب تدريجي دون الوصول الدقيق في زمن محدود.

## Slide 5 — Physics relationships and sign conventions | العلاقات الفيزيائية وإشارة التيار

**Show:** `outputs/physics_relationships.png`.

**Say:** “At fixed SoC, charging voltage versus inward current has slope plus R. The familiar minus-R line uses outward discharge current. We display both conventions explicitly. The curved OCV graph is an illustrative alternative; our exact-solution engine uses affine OCV.”

**بالعربية:** «لازم نثبت حالة الشحن عند تفسير ميل الجهد مع التيار. إذا اعتبرنا تيار الشحن الداخل موجبًا، الميل يكون موجب R. الميل سالب R ينطبق لو التيار الموجب خارج البطارية أثناء التفريغ. أيضًا المنحنى غير الخطي لجهد الدائرة المفتوحة مثال توضيحي فقط؛ الحل التحليلي والمعايرة هنا يستخدمان العلاقة الخطية.»

**Point to:** linear CC SoC growth; rate proportional to current; curved OCV; exponential current taper; straight semilog current plot.

**Terms:** slope / ميل؛ sign convention / اتفاقية الإشارة؛ nonlinear / غير خطي؛ semilog graph / رسم بمحور لوغاريتمي واحد.

## Slide 6 — Euler, Heun and RK4 | طرق الحل العددي

**Show:** a compact solver table from Part 2 of the report.

| Method | Main idea | Global error | Arabic explanation |
|---|---|---|---|
| Euler | one starting slope | $O(h)$ | نستخدم ميل بداية الخطوة |
| Heun | predictor plus averaged slopes | $O(h^2)$ | نتنبأ ثم نصحح بمتوسط الميلين |
| RK4 | four weighted slopes | $O(h^4)$ | نستخدم أربعة ميول بأوزان محددة |

**Say:** “All three methods are exact during ideal CC because the derivative is constant. Their accuracy differences appear in CV. Formal orders assume a smooth regime and sufficiently small steps.”

**بالعربية:** «كون RK4 أعلى رتبة لا يعني أن كل النتائج مضمونة مع أي خطوة زمنية. لازم الخطوة مناسبة ونحدد الانتقال بين المراحل بشكل صحيح. في CC المشتقة ثابتة، لذلك الطرق الثلاث تتفق تقريبًا تمامًا.»

**Terms:** step size / حجم الخطوة الزمنية؛ local defect / خطأ خطوة واحدة؛ global error / الخطأ المتراكم؛ convergence order / رتبة التقارب.

## Slide 7 — Convergence and switching drift | التقارب وانحراف زمن الانتقال

**Show:** `outputs/convergence.png` and Section 2.

**Say:** “We halve the step and measure the observed order. A naive grid check delays crossover by less than one step. Higher-order integration does not fix that timing lag. Our event-aware solver splits a step at the crossover.”

**بالعربية:** «لو نفحص شرط الانتقال فقط عند نهاية الخطوة، قد نتأخر عن الزمن الصحيح. الطرق الثلاث تعطي التأخير نفسه هنا لأن مرحلة CC محسوبة بدقة في كل الطرق. الحل هو تحديد الحدث داخل الخطوة، ثم إكمال باقي الخطوة في CV.»

**Extra analytical point:** timing lag is $O(h)$, but because this model's vector field is continuous at crossover, the induced state defect begins at $O(h^2)$. Event-grid alignment can make observed orders irregular.

**بالعربية:** «خطأ الزمن لا يتحول دائمًا إلى خطأ حالة من الرتبة نفسها. في نموذجنا ميل الحالة مستمر عند الانتقال، لذلك أول حد في خطأ الحالة بسبب التأخير يكون تربيعيًا.»

**Chattering:** repeated mode toggling / تبديل سريع ومتكرر بين المراحل. A one-way CC→CV latch avoids it; coarse-step state oscillation is a different issue.

## Slide 8 — Independent GUI calculations | أقسام حساب مستقلة

**Show:** the five app tabs.

**Say:** “Section 1 computes a charging trajectory and event times. Section 2 independently studies solver error. Section 3 independently fits experimental data. The physics panel studies direct relationships. Export records all configurations, so different assumptions are visible.”

**بالعربية:** «كل قسم له مدخلاته وزر حساب خاص به. المعايرة في القسم الثالث لا تغيّر نتائج القسم الأول أو الثاني تلقائيًا. لو أردنا مقارنة نفس البطارية بين الأقسام، ندخل القيم نفسها بوضوح. ملف التصدير يسجل إعدادات كل قسم لمنع الخلط.»

**Demo transition:** “Now we will test parameter recovery using data whose true parameters are known.” / «الآن نجرب استرجاع معاملات معروفة من بيانات مُولَّدة بالمحاكاة.»

## Slide 9 — Parameter calibration | تقدير معاملات النموذج

**Show:** Section 3 before/after metrics and `outputs/calibrated_overlay.png`.

$$
\hat\theta=\arg\min_{\theta\in\mathcal B}\sum_{c,i}
\left(\frac{\hat y_c(t_i;\theta)-y_{c,i}}{\sigma_c}\right)^2.
$$

**Say:** “We fit capacity, resistance and initial SoC while holding independently chosen circuit assumptions fixed. Dividing by measurement scales makes the multichannel objective meaningful. Exact trajectories keep numerical step error out of fitted parameters.”

**بالعربية:** «نختار قيم المعاملات التي تصغّر مجموع مربعات الفروق بين النموذج والبيانات. نقسم فروق كل قناة على مقياس عدم اليقين المناسب، لأننا لا نجمع الفولت والأمبير مباشرة. نستخدم الحل التحليلي أثناء الملاءمة حتى لا نعوّض خطأ الحل العددي بتغيير معاملات البطارية.»

**Synthetic result:** true $Q=2.12$ Ah, $R=0.18$ Ω, $s_0=0.23$; fitted approximately $2.1205$ Ah, $0.1803$ Ω, $0.23045$. These are known-model recovery results, not proof of real-cell accuracy.

**Terms:** least squares / المربعات الصغرى؛ parameter identifiability / إمكانية تحديد المعاملات من البيانات؛ in-sample / على البيانات المستخدمة في الملاءمة.

## Slide 10 — Metrics and residual diagnosis | مقاييس الخطأ وتحليل البواقي

**Show:** `outputs/residuals.png` and per-channel MAE/RMSE/max-error table.

**Say:** “Residual means experiment minus model. MAE measures average absolute disagreement, RMSE emphasizes larger differences, and maximum error finds the worst sampled mismatch. Patterns suggest missing physics but do not uniquely identify a cause.”

**بالعربية:** «الباقي هو القيمة التجريبية ناقص توقع النموذج. لو البواقي عشوائية وصغيرة حول الصفر، قد تكون متوافقة مع ضوضاء القياس. لو ظهر اتجاه منتظم، نراجع النموذج أو الحساسات أو توقيت القياس. بواقي التيار في نهاية CV قد تشير إلى ثابت زمني غير مناسب.»

**Critical point:** ideal CV voltage is clamped, so it alone cannot identify resistance or capacity. Coulomb-counted SoC is correlated with measured current; do not count it as independent validation.

**Terms:** residual / باقي أو فرق القياس عن النموذج؛ bias / انحياز منتظم؛ noise / ضوضاء؛ validation / تحقق ببيانات مستقلة.

## Slide 11 — Experiment and safety | التجربة والسلامة

**Show:** compatible dedicated charger → protected cell, with voltage/current/temperature logging.

**Say:** “A physical experiment requires a supervised setup, a protected cell and a documented charger matched to the chemistry. We log cell voltage, cell current and time, with temperature monitoring. Our fallback dataset allows a complete software demo without hardware.”

**بالعربية:** «التطبيق لا يتحكم في شاحن حقيقي. التجربة تحتاج إشراف المعمل وشاحنًا مناسبًا لنوع الخلية وحدود الشركة المصنعة. لا نختبر الشحن الزائد أو القصر عمدًا. نوضح بصراحة إذا كانت البيانات مُحاكاة، ونحتاج تجربة مستقلة إذا أردنا ادعاء تحقق فيزيائي.»

**CSV:** `time_sec,voltage_v,current_a,soc_est`; seconds, volts, positive inward amperes and SoC fraction. Omit unavailable SoC rather than inventing values.

## Slide 12 — Reproducible export and conclusion | التصدير وقابلية إعادة النتائج

**Show:** the ZIP button, then the archive's summaries, parameter/error CSVs, figures and source.

**Say:** “Our export contains the assumptions, results, tables, 300-dpi figures and source code needed to reproduce the analysis. The bonus case is the integrated model, numerical verification, event analysis, calibration and diagnosis. The instructor's rubric determines the mark.”

**بالعربية:** «ملف ZIP يجمع الإعدادات والنتائج والرسوم والكود، بحيث يمكن إعادة الحساب ومراجعة كل رقم. الإضافة الأساسية ليست شكل الواجهة فقط، بل الربط بين الرياضيات والتحقق العددي والبيانات وتحليل الخطأ. التقييم النهائي حسب معايير الدكتور.»

## Rehearsed 3-minute live-demo checklist | خطوات العرض الحي

1. Section 1: defaults, termination off. Point to $t_{sw}\approx4884.42$ s and explain asymptotic 100% versus a finite 95% target. **بالعربية:** «لحظة الانتقال محددة، لكن الوصول الدقيق إلى الحد النهائي ليس زمنًا محدودًا.»
2. Section 2: set its own initial SoC to 0.90 and base step to 80 s; press **Calculate convergence**. Show global orders near 1/2/4 and local orders near 2/3/5. Restore 0.20 for switching drift. **بالعربية:** «نبدأ داخل CV لعزل دقة طرق الحل عن تأثير الانتقال.»
3. Section 3: keep defaults and seeded sample; press **Auto-calibrate**. Reveal ground truth and compare errors. **بالعربية:** «هذه بيانات محاكاة؛ نعرف القيم الأصلية لاختبار استرجاع المعاملات.»
4. Physics tab: show $+R$ charging and $-R$ discharge, then change curvature and press its Calculate button. **بالعربية:** «هذا التغيير يؤثر على الرسم التوضيحي فقط.»
5. Export tab: download ZIP and open `summary.md`, `tables/calibrated_parameters.csv`, and `figures/physics_relationships.png`.

Keep `outputs/presentation_bundle.zip` ready as an offline fallback. Form changes apply only after submission. Do not imply calibration automatically changes another section.

## Likely professor questions | أسئلة متوقعة وإجابات مختصرة

| Question | English answer | ملاحظات الإجابة بالعربية |
|---|---|---|
| Why first order? | SoC is the sole dynamic storage state; voltage/current are algebraic outputs. | عندنا متغير حالة ديناميكي واحد. إضافة الاستقطاب أو الحرارة تحتاج معادلات أخرى. |
| Why 3600? | Capacity is Ah; time is seconds. | الأمبير ساعة يساوي 3600 كولوم. |
| Why is the charging V–I slope positive? | Current is positive inward: $V=U+RI$. Minus R uses outward current. | الإشارة تعتمد على اتجاه التيار المتفق عليه، وليست تناقضًا في قانون أوم. |
| Is OCV always nonlinear? | Real OCV may be nonlinear; we use an affine approximation for a transparent exact benchmark. | الرسم المنحني مثال تعليمي، وليس منحنى قياس حقيقي أو نموذج المعايرة الحالي. |
| Why not stop at Vmax? | Vmax begins CV; current cutoff ends charging. | شرط الانتقال مختلف عن شرط الإيقاف. |
| Why not fit Q and efficiency together? | This model identifies their ratio, not both independently. | نحتاج معلومة مستقلة لفصل تأثير السعة عن الكفاءة. |
| Can CV voltage alone identify parameters? | No, it is fixed at Vmax; current and independent anchors are needed. | ثبات الجهد يخفي معلومات عن المعاملات التي نريد تقديرها. |
| Why RK4 if an exact solution exists? | To verify methods against a known answer and prepare for richer models. | الحل التحليلي مرجع ممتاز لاختبار صحة الكود والرتبة العددية. |
| Does small training RMSE prove physical accuracy? | No; use a separate validation run with fixed parameters. | انخفاض خطأ الملاءمة لا يغني عن تجربة مستقلة. |
| Does CC prove thermal runaway? | No, it predicts linear overcharge only; temperature dynamics are absent. | لا نستنتج ظاهرة حرارية من نموذج لا يحتوي معادلة للحرارة. |
| Where is chattering? | The one-way latch prevents it; noisy reversible logic could chatter. | اهتزاز الحل العددي بسبب خطوة كبيرة مختلف عن التبديل المتكرر بين الأوضاع. |
| What is the best solver? | It depends on accuracy, cost, event handling and model uncertainty. | زيادة الرتبة وحدها لا تعالج خطأ الحدث أو قصور النموذج. |

## Mini glossary | قاموس سريع

| English | Simple English meaning | العربية |
|---|---|---|
| ODE | equation relating a state and its rate of change | معادلة تفاضلية عادية |
| Initial condition | state at the start | شرط ابتدائي |
| Predictor–corrector | predict a step, then improve it | متنبئ–مصحح |
| Truncation error | error from replacing continuous evolution with a finite formula | خطأ القطع |
| Event location | finding when a switching condition is met | تحديد زمن الحدث |
| Phase line | arrows showing the direction of state evolution | خط الطور |
| MAE | mean absolute error | متوسط الخطأ المطلق |
| RMSE | root mean square error | الجذر التربيعي لمتوسط مربعات الخطأ |
| Hysteresis | different thresholds for switching in opposite directions | فرق بين عتبتي التبديل لمنع الاهتزاز |
| Reproducibility | repeating the analysis from recorded code, data and settings | قابلية إعادة إنتاج النتائج |
