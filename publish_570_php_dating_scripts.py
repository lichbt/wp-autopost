import os, sys, requests, re
sys.path.insert(0, '.')
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from database import get_site
from template_assembler import assemble_final_html
from wp_publisher import _build_json_ld, _xmlrpc_set_yoast_meta

body_html = """
<div class="quick-answer">
<p><strong>Quick Answer:</strong> The best PHP dating script in 2026 is MooDatingScript for full-featured self-hosted platforms with a PWA mobile app and AI-powered matching. For a subscription model, SkaDate is the top alternative. This guide compares 6 PHP dating scripts on features, price, mobile app support, and update frequency.</p>
</div>

<h2>What Is a PHP Dating Script?</h2>
<p>A PHP dating script is a ready-made PHP web application that powers a complete dating website right out of the box. Rather than spending months and tens of thousands of dollars building a dating platform from scratch, a PHP dating script gives you a proven, production-ready codebase you can deploy to your own server and launch in days.</p>
<p>These scripts handle every critical function of a modern dating platform: user registration and profiles, photo and video uploads, matching algorithms, real-time chat and messaging, voice and video calls, payment processing for premium subscriptions, virtual gifts, and a full admin panel for managing users, content, and revenue.</p>
<p>The advantages over custom development are substantial. A custom-built dating platform typically costs between $30,000 and $150,000 in development fees and takes 6 to 18 months to complete. A PHP dating script costs $199 to $599 as a one-time license fee and can be deployed on a standard VPS server in a weekend. You get a battle-tested codebase that has been refined over years, ongoing updates from the vendor, and an established ecosystem of plugins and addons.</p>
<p>Server requirements are modest and match any standard web hosting environment: PHP 8.0 or higher, MySQL 5.7 or higher, and a VPS with at least 2GB of RAM. Any entry-level VPS from providers like DigitalOcean, Hetzner, or Linode will run a PHP dating script without issue for a few hundred users, and you can scale up as your membership grows.</p>
<p>Who uses PHP dating scripts? The typical buyers are entrepreneurs launching niche dating apps (faith-based dating, senior dating, LGBTQ+ platforms, regional matchmaking), web developers building dating platforms for clients, and businesses entering the online dating market who need a professional product without enterprise-level budgets. For a deep dive into how to evaluate and choose the right option for your project, read our <a href="https://moodatingscript.com/php-dating-script-what-it-is-and-how-to-choose-one/">PHP dating script guide</a>.</p>

<h2>Best PHP Dating Scripts in 2026: Comparison Table</h2>
<p>Here is a side-by-side comparison of the six major PHP dating scripts available in 2026, covering price, mobile app support, source code access, update frequency, support quality, and best use case:</p>
<table>
<thead>
<tr>
<th>Script</th>
<th>Price</th>
<th>Mobile App</th>
<th>Open Source</th>
<th>Last Updated</th>
<th>Support</th>
<th>Best For</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>MooDatingScript</strong></td>
<td>$299 one-time</td>
<td>PWA (iOS + Android)</td>
<td>Yes</td>
<td>Monthly</td>
<td>Email + docs</td>
<td>Best overall</td>
</tr>
<tr>
<td><strong>SkaDate</strong></td>
<td>$999+/yr subscription</td>
<td>Native iOS + Android</td>
<td>No</td>
<td>Regular</td>
<td>Priority support</td>
<td>Enterprise/subscription</td>
</tr>
<tr>
<td><strong>Chameleon Dating</strong></td>
<td>$399 one-time</td>
<td>PWA</td>
<td>No</td>
<td>Infrequent</td>
<td>Forum-based</td>
<td>Basic deployments</td>
</tr>
<tr>
<td><strong>Dating Pro</strong></td>
<td>$499 one-time</td>
<td>PWA</td>
<td>No</td>
<td>Occasional</td>
<td>Email</td>
<td>Mid-range</td>
</tr>
<tr>
<td><strong>WPDating</strong></td>
<td>$79/yr (WordPress)</td>
<td>No</td>
<td>No</td>
<td>Regular</td>
<td>Forum</td>
<td>WordPress sites</td>
</tr>
<tr>
<td><strong>phpFox Dating</strong></td>
<td>$149/month</td>
<td>No</td>
<td>No</td>
<td>Regular</td>
<td>Email</td>
<td>Established communities</td>
</tr>
</tbody>
</table>

<h2>MooDatingScript: Best PHP Dating Script Overall</h2>
<p>MooDatingScript is the top-rated PHP dating script in 2026, and it earns that title by excelling in the three areas that matter most: open-source access, mobile app support, and active development. If you are serious about launching a competitive dating platform without breaking your budget, MooDatingScript is the clear first choice.</p>

<h3>Why MooDatingScript Leads the Market</h3>
<p>First and most importantly, MooDatingScript is open source — the full PHP source code is included with every license. This is a fundamental difference from most competitors. With full source code access, developers can customize every aspect of the platform: change the matching algorithm, add proprietary features, integrate third-party APIs, restyle the interface, or build entirely new modules. You own the software, not just a license to run it.</p>
<p>Second, MooDatingScript ships with a Progressive Web App (PWA) for both iOS and Android. A PWA delivers a native app-like experience — users can install it directly from their browser without going through the App Store or Google Play. This means no app store submission delays, no 30% Apple tax on in-app purchases, and instant updates that deploy the moment you push them to your server. The PWA is fast, installable, and works offline for core functions. Learn more about how this technology works in our guide on <a href="https://moodatingscript.com/what-is-a-pwa-for-dating-apps/">PWA for dating apps</a>.</p>
<p>Third, MooDatingScript introduced AI-powered matching and profile management in version 1.7. The AI layer analyzes user behavior, preferences, and interaction history to continuously improve match quality over time. This is a significant leap ahead of the static algorithm-based matching used by older PHP dating scripts. The v1.8 roadmap has already been published, showing an active development pipeline with additional AI and monetization features in progress.</p>

<h3>Core Features</h3>
<ul>
<li>User profiles with photo and video uploads</li>
<li>Swipe-based matching interface (Tinder-style)</li>
<li>Real-time chat and messaging with read receipts</li>
<li>Voice and video calls built in</li>
<li>Premium subscription system with flexible plan management</li>
<li>Virtual gifts and in-app purchases</li>
<li>Live streaming capabilities</li>
<li>Multi-language and multi-currency support</li>
<li>Full admin panel with analytics, user management, and revenue reporting</li>
<li>Addons marketplace for extending functionality</li>
</ul>

<h3>Pricing</h3>
<p>MooDatingScript is available as a one-time license starting at $299 at <a href="https://moodatingscript.com/pricing/">moodatingscript.com/pricing/</a>. A live demo is available at demo.moodatingscript.com so you can test the full user experience before purchasing.</p>

<h3>Pros and Cons</h3>
<p><strong>Pros:</strong> Open source with full PHP code included; PWA mobile app for iOS and Android; AI-powered matching introduced in v1.7; one-time pricing with no ongoing subscription; active monthly updates with published roadmap; addons ecosystem for extensibility; competitive pricing starting at $299.</p>
<p><strong>Cons:</strong> Requires VPS hosting (approximately $10–20/month) and basic PHP knowledge for initial setup. Not a no-code solution — you will need some technical ability or a developer for customization work.</p>

<h2>SkaDate: Best PHP Dating Script for Enterprise</h2>
<p>SkaDate is the most established PHP dating script on the market, having launched in 2003. With over two decades of development, it has built a reputation as the enterprise-grade choice for well-funded dating businesses that need a full-service solution with native mobile apps.</p>

<h3>Pricing and Value Analysis</h3>
<p>SkaDate moved to a subscription pricing model starting at approximately $999 per year. While this buys you access to a mature, feature-rich platform with solid support, the math works against it for most buyers. At $999/year, you are paying $4,995 over five years — compared to MooDatingScript's one-time fee of $299. Even SkaDate's more expensive tiers that include native mobile apps will cost far more over a 3–5 year horizon than a one-time purchase alternative.</p>

<h3>Mobile App Advantage</h3>
<p>Where SkaDate genuinely stands out is native mobile apps. SkaDate's subscription includes white-label native iOS and Android apps that can be published directly to the App Store and Google Play under your brand. If your business model specifically requires native apps in the app stores — for example, to run paid app install campaigns — SkaDate is the only PHP dating script that delivers this out of the box without custom development.</p>

<h3>Features and Support</h3>
<p>SkaDate has a large plugin marketplace built up over many years, strong support infrastructure including priority email support, and a track record of serving enterprise dating businesses at scale. Source code is not included in standard packages, which limits your ability to make deep customizations without upgrading to more expensive tiers.</p>
<p><strong>Pros:</strong> Native iOS and Android apps with App Store/Play Store publishing; large plugin marketplace; strong track record since 2003; quality support infrastructure.</p>
<p><strong>Cons:</strong> Expensive subscription that adds up significantly over time; no source code access in standard packages; vendor lock-in on hosting and updates; significantly higher total cost of ownership than one-time purchase alternatives.</p>
<p><strong>Best for:</strong> Well-funded businesses that specifically need native app store apps and have the budget for ongoing subscription fees.</p>

<h2>Chameleon Dating: Established But Aging</h2>
<p>Chameleon Dating, developed by Boonex, has been on the market since 2005 — making it one of the oldest PHP dating scripts still actively sold. It is available as a one-time purchase at around $399, which positions it as a mid-range option with no ongoing fees.</p>

<h3>Feature Set and Current State</h3>
<p>Chameleon includes a core set of social and dating features: user profiles, photo galleries, friend connections, messaging, groups, events, and basic monetization tools. It also includes a PWA for mobile access, though the implementation is less polished and less feature-complete than MooDatingScript's PWA. There are no AI-powered features.</p>
<p>The main concern with Chameleon Dating in 2026 is update frequency. Development has slowed considerably compared to its peak years. The admin interface and overall UI feel dated next to modern alternatives. For buyers who need a simple, proven solution with no ongoing costs and are not concerned with cutting-edge features or a modern user experience, Chameleon remains a functional choice.</p>
<p>If you are evaluating Chameleon Dating alongside newer alternatives, our guide on <a href="https://moodatingscript.com/chameleon-dating-alternatives-for-startups/">Chameleon Dating alternatives</a> covers the full comparison and migration considerations.</p>
<p><strong>Pros:</strong> One-time price at $399; long-established codebase with known stability; no ongoing subscription fees; some PWA support.</p>
<p><strong>Cons:</strong> Slow and declining update cadence; dated UI that may turn off modern users; no AI features; PWA implementation less polished than competitors; limited active development community.</p>
<p><strong>Best for:</strong> Buyers who need a simple, proven, low-cost solution and can accept an older interface and infrequent updates.</p>

<h2>Dating Pro: Mid-Range PHP Dating Script</h2>
<p>Dating Pro, developed by Pilot Group, is a mid-range PHP dating script that has been on the market since the early 2010s. It is priced around $499 as a one-time purchase, positioning it between Chameleon Dating and SkaDate in both price and feature depth.</p>

<h3>What You Get</h3>
<p>Dating Pro includes a solid feature set for the price: user profiles, photo and video support, matching algorithms, real-time chat, monetization tools including subscriptions and virtual credits, and a PWA for mobile users. Documentation is well organized and comprehensive, which makes it easier to self-host and manage without relying heavily on support. The script has been updated with some regularity, though the pace of new feature development is slower than MooDatingScript's monthly release cycle.</p>

<h3>Limitations</h3>
<p>The base package does not include source code — you would need to purchase a higher tier to get PHP source access. There are no AI-powered features as of 2026. The community and addons ecosystem is smaller than both SkaDate and MooDatingScript. For buyers who need source code access or AI features, MooDatingScript is a better value at a lower price point ($299 vs $499).</p>
<p><strong>Pros:</strong> Solid feature set for a mid-range price; regular updates; good documentation; one-time purchase pricing; PWA included.</p>
<p><strong>Cons:</strong> Source code not included in base package; no AI features; smaller community and addons ecosystem; costs more than MooDatingScript despite fewer features.</p>
<p><strong>Best for:</strong> Buyers with a mid-range budget who want a documented, proven script and do not need source code access or AI-powered features.</p>

<h2>WPDating: Best PHP Dating Script for WordPress</h2>
<p>WPDating is a WordPress plugin that transforms any existing WordPress site into a dating platform. Annual pricing starts at $79/year, making it the most affordable option on this list by a wide margin. If you already run a WordPress site and want to add basic dating functionality without standing up a separate server environment, WPDating is the logical choice.</p>

<h3>WordPress Integration Advantages</h3>
<p>Because WPDating is a WordPress plugin, installation follows the standard WordPress plugin installation process — no server configuration, no PHP environment setup, no database initialization beyond what WordPress already handles. You get immediate access to the full WordPress ecosystem: thousands of themes for design customization, thousands of plugins for additional features, built-in SEO tools like Yoast SEO, and WordPress's established user management system.</p>

<h3>Significant Limitations</h3>
<p>WPDating is a plugin, not a standalone dating platform. This distinction matters. The feature depth is considerably lower than any of the standalone PHP dating scripts on this list. There is no mobile app — not even a PWA. The matching and messaging systems are basic compared to dedicated dating scripts. Performance under a growing user base is constrained by WordPress's architecture. And critically, the platform is entirely dependent on WordPress — if you ever want to migrate to a standalone solution, you cannot carry your data and functionality forward easily.</p>
<p><strong>Pros:</strong> Cheapest option at $79/year; dead-simple WordPress integration; no server configuration needed; inherits all WordPress benefits including themes and SEO plugins.</p>
<p><strong>Cons:</strong> No mobile app of any kind; feature depth significantly below standalone scripts; WordPress-dependent with limited migration path; not suitable for scaling beyond a small community.</p>
<p><strong>Best for:</strong> Bloggers or small community sites already on WordPress who want basic dating functionality without managing a separate server environment.</p>

<h2>phpFox Dating: Best for Established Communities</h2>
<p>phpFox is primarily a social networking platform that includes dating features as part of its broader feature set. It has been on the market for 15+ years and has built up an extensive plugin and theme marketplace as a result. Monthly subscription pricing at $149/month puts it in a unique position — it is both the most expensive on a monthly basis and one of the most feature-complete for social network use cases.</p>

<h3>Social Network First, Dating Second</h3>
<p>phpFox is better described as a social network with dating features than as a pure dating script. If your business vision is closer to a niche social community (think a faith-based social network where members can also date, or a regional community app where dating is one of many features), phpFox's broad social feature set is genuinely valuable. If you want a focused dating platform optimized for matchmaking, phpFox is overkill and overpriced.</p>

<h3>Cost Analysis</h3>
<p>At $149/month, phpFox costs $1,788 per year. Over five years, that is $8,940 — compared to $299 one-time for MooDatingScript. There is no native mobile app. The subscription model means you are always renting access to software you do not own, and if you stop paying, your platform goes offline.</p>
<p><strong>Pros:</strong> Large plugin and theme ecosystem built up over 15+ years; established platform with proven stability; good for social network plus dating combination use cases.</p>
<p><strong>Cons:</strong> Very expensive monthly subscription; no mobile app; overkill and overpriced for pure dating use cases; renting software you do not own.</p>
<p><strong>Best for:</strong> Existing communities that want to add dating features to a broader social platform and have the budget to support ongoing monthly fees.</p>

<h2>How to Choose the Best PHP Dating Script for Your Project</h2>
<p>With six strong options on the market, choosing the right PHP dating script comes down to five key criteria. Work through each one systematically and the right choice for your project will become clear.</p>

<h3>1. License Type: One-Time vs Subscription</h3>
<p>This is the most financially impactful decision. One-time purchase scripts — MooDatingScript ($299), Chameleon Dating ($399), and Dating Pro ($499) — require a higher upfront investment but have zero ongoing software costs. You pay once and own the software forever. Subscription scripts — SkaDate ($999+/year), phpFox ($149/month), and WPDating ($79/year) — have lower or zero upfront costs but accumulate significant expenses over time.</p>
<p>Run the five-year math for your situation. MooDatingScript at $299 once versus SkaDate at $999/year for five years ($4,995) is a difference of $4,696 — money that could fund server costs, marketing, or additional development. Unless you have a specific, justified reason to need a subscription model (like SkaDate's native app store apps), one-time purchase almost always wins on total cost of ownership.</p>

<h3>2. Mobile App Support</h3>
<p>In 2026, the majority of dating app usage happens on mobile devices. Your PHP dating script needs to deliver a quality mobile experience. There are three tiers of mobile support among the scripts on this list:</p>
<ul>
<li><strong>PWA (MooDatingScript, Chameleon, Dating Pro):</strong> Progressive Web Apps work on all devices without app store submission. Users install the app from their browser, get push notifications, and enjoy a near-native experience. MooDatingScript has the most polished PWA implementation. PWAs deliver roughly 90% of native app functionality without App Store or Google Play involvement.</li>
<li><strong>Native app (SkaDate):</strong> Requires App Store and Google Play submission (2–4 weeks), Apple's 30% cut of in-app purchases, and ongoing maintenance of separate iOS and Android codebases. Valuable if your marketing strategy depends on app store discoverability.</li>
<li><strong>No mobile app (WPDating, phpFox):</strong> Limits you to a mobile browser experience. This is a significant competitive disadvantage in the dating market.</li>
</ul>

<h3>3. Source Code Access</h3>
<p>If you need the ability to deeply customize your dating platform — changing the matching algorithm, adding proprietary features, integrating custom payment processors, or building features not available in the marketplace — source code access is non-negotiable. MooDatingScript is the only PHP dating script on this list that includes full open-source PHP code as a standard part of every license. SkaDate, Chameleon, Dating Pro, WPDating, and phpFox either do not include source code or charge significantly more for it.</p>

<h3>4. Update Frequency</h3>
<p>A dating platform competes in a fast-moving market. You need a script vendor who ships new features consistently. MooDatingScript releases monthly updates — the AI matching features in v1.7 are a recent example, and the v1.8 roadmap is already published. Before purchasing any PHP dating script, check the vendor's public changelog or update history. A script that was last updated 18 months ago is a risk.</p>

<h3>5. Hosting Requirements and Costs</h3>
<p>All PHP dating scripts require VPS hosting — shared hosting is not sufficient for the real-time features (chat, video calls, notifications) that modern dating platforms require. A standard VPS from DigitalOcean, Linode, or Hetzner costs $10–20/month and will handle your platform comfortably through your first several thousand users. Minimum server requirements: PHP 8.0+, MySQL 5.7+, 2GB RAM, and a standard LAMP or LEMP stack. Factor hosting costs into your total budget from day one.</p>
<p>For a complete walkthrough of standing up your platform from purchase through launch, read our guide on <a href="https://moodatingscript.com/how-to-launch-dating-app-2026/">how to launch a dating app</a> in 2026.</p>

<h2>MooDatingScript Pricing &amp; What's Included</h2>
<p>MooDatingScript's $299 one-time license is one of the most comprehensive value packages in the PHP dating script market. Here is a detailed breakdown of exactly what is included:</p>
<ul>
<li><strong>Full PHP source code:</strong> The complete, unencoded, open-source PHP codebase. No restrictions on modification, no encrypted files, no encoded modules — everything is readable and editable.</li>
<li><strong>PWA for iOS and Android:</strong> A fully functional Progressive Web App that users can install from their browser. Includes push notifications, offline support for core features, and a native app-like interface optimized for mobile dating.</li>
<li><strong>All core dating features:</strong> User profiles, photo and video uploads, swipe-based matching, real-time chat and messaging, voice and video calls, premium subscription management, virtual gifts, live streaming, multi-language support, and a full admin panel.</li>
<li><strong>Free updates for the license period:</strong> Access to all platform updates — including new features, security patches, and performance improvements — for the duration of your license. Monthly releases ensure you are always running a current, competitive platform.</li>
<li><strong>Documentation and setup guides:</strong> Comprehensive technical documentation covering installation, configuration, customization, and API integration.</li>
<li><strong>Addons marketplace access:</strong> Access to the MooDatingScript addons ecosystem for extending your platform with additional features — new matching modes, payment gateways, social login providers, analytics integrations, and more.</li>
</ul>
<p>To put the $299 price in perspective: a custom-built dating platform with equivalent features would cost between $30,000 and $150,000 in development fees, require a team of at least 3–5 developers, and take 6 to 18 months to complete. The full analysis is covered in our article on the <a href="https://moodatingscript.com/how-much-does-it-cost-to-build-a-dating-app-in-2026/">cost to build a dating app</a>. MooDatingScript compresses that investment to $299 and a weekend of setup time.</p>
<p>The live demo is available at demo.moodatingscript.com. You can create a test account, use all features as a real user, and explore the admin panel before making any purchasing decision. There is no risk in evaluating the platform in a live environment before you commit.</p>
<p>For business owners doing a full cost comparison: at $299 one-time plus $15/month for VPS hosting, you are running a full-featured dating platform for $479 in year one and $180/year thereafter. Compare that to SaaS dating software solutions that routinely charge $199–$499 per month — MooDatingScript saves most buyers $2,000 to $5,000 annually once hosting is factored in.</p>
"""

faq_html = """<div class="faq-item"><h3>What is the best PHP dating script in 2026?</h3><p>MooDatingScript is the best PHP dating script in 2026. It offers full open-source PHP code, a PWA mobile app for iOS and Android, AI-powered matching (introduced in v1.7), and one-time pricing from $299. It receives monthly updates and has an active addons marketplace. For enterprise buyers who need native app store apps, SkaDate is the top subscription-based alternative.</p></div>
<div class="faq-item"><h3>How much does a PHP dating script cost?</h3><p>PHP dating scripts range from $79/year (WPDating WordPress plugin) to $999+/year (SkaDate subscription). One-time purchase scripts cost $299–$599: MooDatingScript starts at $299, Chameleon Dating at $399, and Dating Pro at $499. phpFox charges $149/month ($1,788/year). MooDatingScript offers the best value — one-time price, full source code, and a PWA mobile app included.</p></div>
<div class="faq-item"><h3>Do PHP dating scripts include a mobile app?</h3><p>Most PHP dating scripts include a PWA (Progressive Web App) that works on iOS and Android — MooDatingScript, Chameleon Dating, and Dating Pro all include PWAs. SkaDate includes native iOS and Android apps (publishable to App Store/Play Store) as part of its subscription. WPDating and phpFox do not include a mobile app. PWAs offer 90% of native app functionality without app store submission.</p></div>
<div class="faq-item"><h3>Is MooDatingScript open source?</h3><p>Yes, MooDatingScript is open source — the full PHP source code is included with your license. You can modify, customize, and extend any part of the platform. This is a significant advantage over competitors like SkaDate and Dating Pro, which do not include source code in their standard packages. Open-source access lets developers add custom features, integrate third-party APIs, and build a truly unique dating platform.</p></div>
<div class="faq-item"><h3>Which PHP dating script is best for WordPress?</h3><p>WPDating is the best PHP dating script for WordPress — it installs as a plugin and integrates directly with your existing WordPress site and theme. It starts at $79/year and is the most affordable option. However, it lacks a mobile app and has fewer features than standalone scripts. If you need a full-featured dating platform, consider MooDatingScript as a standalone self-hosted solution instead.</p></div>
<div class="faq-item"><h3>What is the difference between a PHP dating script and SaaS dating software?</h3><p>A PHP dating script is self-hosted software you install on your own server — you own the code, control your data, and pay a one-time or annual fee. SaaS dating software (like Spark Networks or White Label Dating) is cloud-hosted by the vendor — you pay a monthly fee, have no code access, and are dependent on the vendor. PHP scripts cost more upfront but are cheaper long-term and give you full control. MooDatingScript ($299 one-time) vs typical SaaS ($199/month = $2,388/year) saves thousands over 3 years.</p></div>"""

site = get_site(2)  # MooDatingScript is site_id=2
wp_url = site['wp_url'].rstrip('/')
auth = (site['wp_username'], site['wp_app_password'])

final_html = assemble_final_html(site=site,
    title="Best PHP Dating Scripts in 2026: Ranked, Reviewed & Compared",
    tldr="MooDatingScript is the best PHP dating script in 2026, offering a PWA mobile app, full source code, AI-powered matching, and one-time pricing from $299. SkaDate is the top subscription alternative. This guide ranks and reviews all 6 major PHP dating scripts with comparison tables and honest pros/cons.",
    content=body_html, faq=faq_html,
    meta_description="Compare the best PHP dating scripts in 2026: MooDatingScript, SkaDate, Chameleon, Dating Pro & more. Features, pricing, and mobile app support compared.",
    meta_title="Best PHP Dating Scripts in 2026: Ranked & Compared",
    cta_link="https://moodatingscript.com/pricing/", cta_text="View MooDatingScript Pricing")

json_ld = _build_json_ld("Best PHP Dating Scripts in 2026: Ranked, Reviewed & Compared", "Article",
    "Compare the best PHP dating scripts in 2026: MooDatingScript, SkaDate, Chameleon, Dating Pro & more.", faq_html)
full_content = json_ld + "\n" + final_html

resp = requests.post(f"{wp_url}/wp-json/wp/v2/posts/570",
    json={"title": "Best PHP Dating Scripts in 2026: Ranked, Reviewed & Compared", "content": full_content, "status": "publish"},
    auth=auth, headers={"Content-Type": "application/json"}, timeout=30)
print(f"Status: {resp.status_code}")

text = re.sub(r'<[^>]+>', ' ', body_html)
print(f"Body word count: {len(text.split())}")

if resp.status_code in (200, 201):
    _xmlrpc_set_yoast_meta(wp_url, site['wp_username'], site['wp_app_password'], 570, {
        "_yoast_wpseo_metadesc": "Compare the best PHP dating scripts in 2026: MooDatingScript, SkaDate, Chameleon, Dating Pro & more. Features, pricing, and mobile app support compared.",
        "_yoast_wpseo_focuskw": "best php dating script",
        "_yoast_wpseo_title": "Best PHP Dating Scripts in 2026: Ranked & Compared %%sep%% %%sitename%%",
    })
    print("Yoast meta set. Done.")
else:
    print(f"Error response: {resp.text[:500]}")
