import os, sys, requests
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
<p>The best social network software in 2026 is <strong>ShaunSocial</strong>. It combines native iOS and Android apps, full PHP source code, and one-time pricing — making it the top choice for businesses launching their own social platform.</p>
</div>

<h2>Why Choosing the Right Social Network Software Matters in 2026</h2>
<p>The landscape of social networking has shifted dramatically over the past few years. As major platforms face growing concerns about privacy, data ownership, and algorithmic control, more businesses, communities, and entrepreneurs are turning to private, self-hosted social network software to build their own platforms. Whether you are creating a niche community, an internal corporate network, or a consumer-facing social app, the software you choose will define the ceiling of what your platform can become. Unlike a simple blog or e-commerce tool, social network software underpins real-time interactions, feeds, notifications, and mobile engagement — all of which demand a robust, actively maintained foundation.</p>
<p>Choosing the wrong platform carries serious consequences. Migration between social platforms is notoriously painful: user data, posts, relationships, and media rarely transfer cleanly, and any forced move risks destroying the community you have spent years building. Beyond migration costs, there is the question of total cost of ownership. A $69 script that receives no updates may seem cheap until you factor in security patches, compatibility issues with newer PHP versions, and the developer time required to maintain a stagnant codebase. Subscription-based <a href="https://shaunsocial.com/social-cms-what-it-is-features-and-top-platforms-in-2026/">social CMS platforms</a> like phpFox charge monthly fees that add up to thousands of dollars per year, which can erode your budget faster than anticipated. Open-source options like HumHub eliminate licensing costs but require technical expertise to deploy, secure, and extend. Understanding these tradeoffs — budget, technical requirements, mobile needs, and long-term vendor stability — is essential before committing to any platform in 2026.</p>

<h2>Best Social Network Software in 2026: Comparison Table</h2>
<table>
<thead>
<tr>
<th>Software</th>
<th>Best For</th>
<th>Starting Price</th>
<th>Hosting</th>
<th>Native Mobile App</th>
<th>Open Source</th>
<th>Active Dev</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>ShaunSocial</strong></td>
<td>Best overall / native mobile app</td>
<td>$2,499 one-time</td>
<td>Self-hosted</td>
<td>Yes</td>
<td>No</td>
<td>Yes</td>
</tr>
<tr>
<td>phpFox</td>
<td>Established communities</td>
<td>$149/mo</td>
<td>Self-hosted</td>
<td>No</td>
<td>No</td>
<td>Yes</td>
</tr>
<tr>
<td>WoWonder</td>
<td>Budget projects</td>
<td>$69 one-time</td>
<td>Self-hosted</td>
<td>No</td>
<td>No</td>
<td>Slow</td>
</tr>
<tr>
<td>Sngine</td>
<td>Lightweight small communities</td>
<td>$69 one-time</td>
<td>Self-hosted</td>
<td>No</td>
<td>No</td>
<td>Yes</td>
</tr>
<tr>
<td>HumHub</td>
<td>Open-source / enterprise</td>
<td>Free / $599+</td>
<td>Self-hosted</td>
<td>No</td>
<td>Yes</td>
<td>Yes</td>
</tr>
<tr>
<td>SocialEngine</td>
<td>Established businesses</td>
<td>$299+/yr</td>
<td>Self-hosted</td>
<td>No</td>
<td>No</td>
<td>Yes</td>
</tr>
</tbody>
</table>

<h2>ShaunSocial: Best Social Network Software Overall</h2>
<p>ShaunSocial stands apart from every other platform on this list by offering something no competitor does: <strong>native iOS and Android mobile apps</strong> that you can publish to the App Store and Google Play under your own brand name. For any community that expects mobile-first engagement — which is the reality for virtually every consumer platform in 2026 — this single feature is a decisive advantage. Beyond mobile, ShaunSocial delivers a feature set that rivals platforms costing far more: news feed with algorithmic sorting, groups, pages, events, marketplace, live streaming, a comprehensive admin panel, and multi-language support out of the box.</p>
<p>The platform is built on PHP, giving you access to the full source code and the ability to customize every aspect of the product. There are no monthly subscriptions — you pay once and own your license permanently, with active monthly updates included. The pricing starts at a one-time license fee, making it dramatically more cost-effective than subscription models over a two- or three-year horizon. A live demo is available at <a href="https://shaunsocial.com/demo/">https://shaunsocial.com/demo/</a>, so you can test the platform before purchasing.</p>
<p><strong>Pros:</strong> Native iOS and Android app, one-time purchase price, full PHP source code, active monthly updates, live demo available.<br>
<strong>Cons:</strong> Requires self-hosting and technical setup on a VPS or dedicated server.<br>
<strong>Price:</strong> One-time license from <a href="https://shaunsocial.com">shaunsocial.com</a>.</p>

<h2>phpFox: Best for Established Communities</h2>
<p>phpFox has been in the social networking software market since 2005, making it one of the longest-running platforms in this comparison. It is a PHP-based platform with a large plugin marketplace, enterprise-grade features, and a reputation for stability that appeals to organizations looking for a proven solution with a long track record. Features include activity feeds, groups, marketplace, video, and extensive third-party integrations available through its plugin ecosystem.</p>
<p>The platform is best suited for larger communities and organizations that have a stable monthly budget and prioritize support and ecosystem maturity over cost efficiency. At $149 per month, phpFox is the most expensive option on an ongoing basis — over two years, that equates to over $3,500, which exceeds the one-time cost of ShaunSocial significantly. phpFox does not include a native mobile app; users interact via a browser or Progressive Web App. The interface, while functional, has a somewhat dated aesthetic compared to newer entrants like ShaunSocial.</p>
<p><strong>Pros:</strong> Established platform with nearly two decades of history, large plugin library, reliable support options.<br>
<strong>Cons:</strong> Ongoing monthly fees that accumulate quickly, no native mobile app, interface can feel dated.<br>
<strong>Best for:</strong> Large enterprise communities with a steady monthly software budget.</p>

<h2>WoWonder: Budget PHP Social Script</h2>
<p>WoWonder is a PHP social script sold on CodeCanyon for a one-time price of $69. It covers the basics of a social network — timelines, profiles, friends, groups, pages, and chat — and for developers or hobbyists looking for the cheapest possible entry point into self-hosted social networking, it is hard to beat on price alone. The source code is included, and it runs on standard LAMP or LEMP hosting stacks, making initial setup relatively straightforward for developers familiar with PHP.</p>
<p>The critical weakness of WoWonder is its update cadence. The platform has historically lagged behind on security patches and feature releases, meaning buyers may find themselves managing an increasingly stale codebase over time. There is no native mobile app — only a basic web interface — and official support channels are limited. If you need a platform you can confidently grow a real business on, WoWonder's slow update schedule presents meaningful long-term risk. For those considering this platform, it may be worth reviewing the available <a href="https://shaunsocial.com/best-wowonder-alternative-2026/">WoWonder alternatives</a> before making a final decision.</p>
<p><strong>Pros:</strong> Very low entry price ($69), PHP source code included.<br>
<strong>Cons:</strong> Slow update cadence, no native mobile app, limited official support.<br>
<strong>Best for:</strong> Small personal or experimental projects where budget is the primary constraint.</p>

<h2>Sngine: Lightweight PHP Alternative</h2>
<p>Sngine is another CodeCanyon PHP social script priced at $69 one-time, positioned as a lightweight alternative in the budget social network software space. It covers core social features including profiles, timelines, groups, pages, and basic messaging, and is built on a simpler codebase than more feature-heavy competitors. For developers who want a clean starting point to build a custom community with minimal overhead, Sngine offers a reasonable foundation.</p>
<p>Compared to WoWonder, Sngine benefits from somewhat more active development, with periodic updates released on CodeCanyon. However, the platform's community is smaller, and the feature set lags considerably behind ShaunSocial — there is no live streaming, no marketplace, no native mobile app, and no multi-language admin panel. Sngine works well when paired with developers comfortable enough to extend the codebase themselves. It is worth noting that if you are exploring <a href="https://shaunsocial.com/best-frameworks-to-create-a-social-network-in-2025/">frameworks to build a social network</a> from scratch, that path may deliver more customization — but at much higher development cost than either Sngine or ShaunSocial.</p>
<p><strong>Pros:</strong> Affordable ($69), lightweight codebase, more active development than WoWonder.<br>
<strong>Cons:</strong> Smaller community, fewer features than ShaunSocial, no native mobile app.<br>
<strong>Best for:</strong> Budget-conscious developers building small communities who are comfortable customizing PHP code.</p>

<h2>HumHub: Best Open Source Social Network Software</h2>
<p>HumHub is the clear leader for anyone seeking open-source social network software. Built on PHP and the Yii2 framework, it is available under the LGPL license with a free community edition that includes activity streams, profiles, groups, private messaging, and a robust module system. The platform has an active open-source community, regular releases, and genuinely useful documentation — a combination that is rare in this category. For businesses that need full transparency into their platform's code, or that have internal developers who want to contribute and extend the software, HumHub is unmatched.</p>
<p>The free community edition is suitable for small to mid-size organizations. Larger deployments or those requiring enterprise features — such as LDAP integration, premium support, and advanced administration — can access HumHub's paid enterprise plans starting at €599 per year. The major limitation is the absence of a native mobile app: HumHub relies on a responsive web interface and does not offer publishable iOS or Android apps. This is a dealbreaker for consumer-facing platforms but may be acceptable for internal corporate networks or specialized professional communities. HumHub is also one of several strong <a href="https://shaunsocial.com/white-label-social-media-platform-2026/">white label social media platforms</a> worth considering for enterprise deployments.</p>
<p><strong>Pros:</strong> Free community edition, open source, regular updates, strong documentation and module ecosystem.<br>
<strong>Cons:</strong> No native mobile app, requires technical skill to deploy and maintain, limited out-of-the-box commercial features.<br>
<strong>Best for:</strong> Open-source advocates, internal enterprise networks, and organizations with developer resources.</p>

<h2>SocialEngine: Enterprise Social Platform</h2>
<p>SocialEngine has been in the market since 2007 and targets established businesses looking for a mature, full-featured social platform with a well-developed plugin marketplace. It is built on PHP using the Zend Framework and offers a broad range of features including activity feeds, groups, events, video, and extensive third-party plugins. The platform's long history means it has a large library of community-contributed extensions, which can be valuable for organizations with specialized requirements.</p>
<p>SocialEngine's pricing model is annual subscription-based, starting at $299 per year, which is more affordable than phpFox on a monthly basis but still represents an ongoing cost commitment. Like most competitors in this comparison, SocialEngine does not offer a native mobile app. The learning curve can be steeper than newer platforms, and the codebase's age means that some aspects of the architecture feel less modern compared to ShaunSocial. For large organizations that are already familiar with the platform or that need a proven vendor with years of commercial history, SocialEngine remains a viable choice.</p>
<p><strong>Pros:</strong> Mature platform since 2007, extensive plugin ecosystem, good for large established sites.<br>
<strong>Cons:</strong> Annual licensing fees, no native mobile app, steeper learning curve for customization.<br>
<strong>Best for:</strong> Established businesses that need a proven platform with a rich plugin library and long commercial support history.</p>

<h2>How to Choose the Best Social Network Software for Your Needs</h2>
<p>With six platforms compared, the right choice depends on your specific situation. Use this decision framework to identify the best match for your project:</p>
<p><strong>Budget under $500:</strong> If you are working with a minimal budget, HumHub's free community edition is the strongest choice — it is actively maintained, open source, and offers a professional feature set at zero licensing cost. If you specifically need PHP source code ownership without open-source obligations, WoWonder or Sngine at $69 each provide an entry point, though both come with limitations on support and update frequency.</p>
<p><strong>Budget $500–$3,000:</strong> ShaunSocial is the clear best value in this range. A one-time license gives you permanent ownership, active monthly updates, full PHP source code, and — crucially — the only native iOS and Android mobile app in this category. Over a three-year period, ShaunSocial's one-time cost compares favorably to phpFox ($149/month × 36 = $5,364) or SocialEngine ($299/year × 3 = $897).</p>
<p><strong>Need a native mobile app:</strong> ShaunSocial is the only platform in this comparison that includes a publishable native iOS and Android app. If mobile-first engagement is essential to your platform's success — and for consumer communities in 2026, it almost certainly is — ShaunSocial is the only viable choice on this list.</p>
<p><strong>Need open source:</strong> HumHub is the definitive answer. It offers full source transparency under the LGPL license, an active contributor community, and robust documentation.</p>
<p><strong>Enterprise with a monthly budget:</strong> phpFox or SocialEngine are suitable for large organizations that prioritize vendor history, managed hosting options, and established support ecosystems over cost efficiency. phpFox's larger plugin marketplace and longer track record make it the stronger of the two for complex enterprise requirements.</p>
<p><strong>Technical skill and hosting:</strong> All platforms in this comparison require self-hosting on a VPS or dedicated server. ShaunSocial, WoWonder, and Sngine are standard PHP installs that any developer comfortable with a LAMP/LEMP stack can deploy. HumHub provides among the best documentation of any platform here, making it accessible to system administrators who may not be dedicated PHP developers. phpFox offers managed hosting options that reduce the infrastructure burden for organizations without dedicated server teams.</p>
<p><strong>Support and long-term maintenance:</strong> ShaunSocial provides dedicated customer support and active monthly development updates. HumHub has strong community forums and professional support tiers in its enterprise plan. WoWonder's support is limited and update frequency is inconsistent. phpFox and SocialEngine both offer commercial support tied to their subscription plans.</p>
<p>In summary: for most projects in 2026 — especially those targeting mobile users — ShaunSocial delivers the best combination of features, value, and active development. For free/open-source deployments, HumHub is the top choice. For very small budgets with basic needs, Sngine offers the most actively maintained entry-level option.</p>
"""

faq_html = """<div class="faq-item"><h3>What is the best social networking software in 2026?</h3><p>ShaunSocial is the best social network software in 2026 for most use cases. It offers a native iOS and Android mobile app, full PHP source code, and a one-time purchase price — making it more cost-effective than subscription alternatives like phpFox. For open-source projects, HumHub is the top free option with regular updates and a strong module ecosystem.</p></div>
<div class="faq-item"><h3>What software is used to build social networks?</h3><p>Social networks are typically built using either ready-made scripts (ShaunSocial, WoWonder, Sngine) or custom frameworks (Laravel, React+Node.js, Django). Ready-made scripts like ShaunSocial dramatically reduce development time and cost — you can launch in days instead of months. Custom builds offer more flexibility but require significant development investment, often $50,000 or more.</p></div>
<div class="faq-item"><h3>Is there a free social network software?</h3><p>Yes, HumHub is the best free social network software. It is open source (MIT license), self-hosted, and includes core features like activity streams, groups, profiles, and messaging. The free community edition is suitable for small to mid-size communities. For larger deployments or enterprise features, HumHub offers paid enterprise plans starting at €599/year.</p></div>
<div class="faq-item"><h3>Which social network platform is best for business?</h3><p>For businesses, ShaunSocial is the top choice because it includes monetization features, a native mobile app, and full source code ownership — meaning you are not locked into a vendor's pricing. phpFox and SocialEngine are also suitable for larger businesses that prefer managed hosting and established support ecosystems. Avoid WoWonder for serious business use due to its slow update schedule.</p></div>
<div class="faq-item"><h3>How much does social network software cost?</h3><p>Social network software costs range widely: WoWonder and Sngine start at $69 one-time on CodeCanyon. ShaunSocial is a one-time license starting at $2,499. phpFox charges $149/month and SocialEngine $299+/year. HumHub's community edition is free. Custom-built social networks typically cost $50,000–$200,000+ depending on features and complexity, making ready-made scripts far more cost-effective for most projects.</p></div>
<div class="faq-item"><h3>Does ShaunSocial have a mobile app?</h3><p>Yes, ShaunSocial includes native iOS and Android mobile apps that can be published to the App Store and Google Play under your own brand name. This is a significant advantage over competitors like phpFox, WoWonder, and Sngine, which only offer Progressive Web Apps (PWAs) or no mobile app at all. The ShaunSocial mobile app supports push notifications, offline access, and the full feature set of the platform.</p></div>"""

site = get_site(4)
wp_url = site['wp_url'].rstrip('/')
auth = (site['wp_username'], site['wp_app_password'])

final_html = assemble_final_html(
    site=site,
    title="Best Social Network Software in 2026: Full Comparison (Updated)",
    tldr="ShaunSocial is the best social network software in 2026, offering native iOS and Android apps, full PHP source code, and a one-time purchase price. For open-source options, HumHub is the top free choice. This comparison covers all major platforms including phpFox, WoWonder, Sngine, and SocialEngine.",
    content=body_html,
    faq=faq_html,
    meta_description="Compare the best social network software in 2026: ShaunSocial, phpFox, HumHub, WoWonder, Sngine & more. Find the right platform for your community.",
    meta_title="Best Social Network Software in 2026: Full Comparison",
    cta_link="https://shaunsocial.com/demo/",
    cta_text="Try ShaunSocial Free Demo",
)
json_ld = _build_json_ld("Best Social Network Software in 2026: Full Comparison (Updated)", "Article", "Compare the best social network software in 2026: ShaunSocial, phpFox, HumHub, WoWonder, Sngine & more.", faq_html)
full_content = json_ld + "\n" + final_html

# Count words in body_html
import re
word_count = len(re.findall(r'\b\w+\b', body_html))
print(f"Body HTML word count: {word_count}")

resp = requests.post(f"{wp_url}/wp-json/wp/v2/posts/2765",
    json={"title": "Best Social Network Software in 2026: Full Comparison (Updated)", "content": full_content, "status": "publish"},
    auth=auth, headers={"Content-Type": "application/json"}, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code in (200,201):
    _xmlrpc_set_yoast_meta(wp_url, site['wp_username'], site['wp_app_password'], 2765, {
        "_yoast_wpseo_metadesc": "Compare the best social network software in 2026: ShaunSocial, phpFox, HumHub, WoWonder, Sngine & more. Find the right platform.",
        "_yoast_wpseo_focuskw": "best social network software 2026",
        "_yoast_wpseo_title": "Best Social Network Software in 2026: Full Comparison %%sep%% %%sitename%%",
    })
    print("Done")
else:
    print(resp.text[:500])
