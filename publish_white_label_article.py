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

body_html = """<div class="quick-answer">
<p>A white-label social media platform is software you fully brand as your own — no vendor logos visible to your users. The best in 2026: <strong>ShaunSocial</strong> (self-hosted, one-time price, native mobile app), <strong>Bettermode</strong> (cloud SaaS), and <strong>HumHub</strong> (open source). Choose based on your budget, technical capabilities, and whether you need a native mobile app.</p>
</div>

<h2>What Is a White Label Social Media Platform?</h2>
<p>A white-label social media platform is software where all vendor branding has been completely removed and replaced with your own brand identity — your name, logo, colors, and domain. When users sign up and engage on your platform, they see only your brand, never the name or logo of the company that built the underlying software. This is fundamentally different from simply "adding your logo" to a tool; true white-labeling means the vendor is invisible across every page, email notification, mobile app, and user-facing touchpoint.</p>
<p>Four key characteristics define a genuine white-label social platform: (1) <strong>Custom domain</strong> — your community lives at yourbrand.com, never at vendor.com or a subdomain of the vendor's site. (2) <strong>Full brand control</strong> — you can change the platform name, swap in your logo, apply your color palette, and update every interface element to match your identity. (3) <strong>No vendor watermarks</strong> — no "powered by" footer badges, no vendor splash screens, no attribution links anywhere in the user interface. (4) <strong>Modular features</strong> — you can enable or disable specific modules (groups, events, marketplace, live video) to match your use case rather than exposing a generic feature set to your users. It is also important to distinguish white-labeling from related concepts: open-source software is about code licensing and the right to view or modify code — it says nothing about branding. SaaS-with-branding is a partial white-label where the vendor's name may still appear in billing flows, support emails, or mobile app listings. Who uses white-label social platforms? The list is broad: businesses building internal employee engagement networks, brands building customer loyalty communities, agencies building community products for clients, NGOs managing volunteer and donor networks, educational institutions building student or alumni communities, and hobby groups building interest-based social spaces all find white-label platforms essential for presenting a cohesive brand experience.</p>

<h2>Best White Label Social Media Platforms in 2026: Comparison Table</h2>
<p>The table below summarizes the eight leading white-label social media platforms in 2026 across the most critical decision criteria.</p>
<table>
<thead>
<tr>
<th>Platform</th>
<th>Starting Price</th>
<th>Hosting</th>
<th>Native Mobile App</th>
<th>Custom Domain</th>
<th>White-Label Depth</th>
<th>Best For</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>ShaunSocial</strong></td>
<td>$2,499 one-time</td>
<td>Self-hosted</td>
<td>Yes (iOS + Android)</td>
<td>Yes</td>
<td>Full (remove all vendor branding)</td>
<td>All-round white-label social network</td>
</tr>
<tr>
<td>Bettermode</td>
<td>$499/month</td>
<td>Cloud SaaS</td>
<td>PWA only</td>
<td>Yes</td>
<td>Full</td>
<td>SaaS community platform</td>
</tr>
<tr>
<td>Hivebrite</td>
<td>$500+/month</td>
<td>Cloud SaaS</td>
<td>PWA only</td>
<td>Yes</td>
<td>Full</td>
<td>Alumni &amp; associations</td>
</tr>
<tr>
<td>HumHub</td>
<td>Free / €599+/yr</td>
<td>Self-hosted</td>
<td>PWA only</td>
<td>Yes</td>
<td>Full</td>
<td>Open source communities</td>
</tr>
<tr>
<td>phpFox</td>
<td>$149/month</td>
<td>Self-hosted</td>
<td>No</td>
<td>Yes</td>
<td>Full</td>
<td>Established communities</td>
</tr>
<tr>
<td>SocialEngine</td>
<td>$299+/year</td>
<td>Self-hosted</td>
<td>No</td>
<td>Yes</td>
<td>Full</td>
<td>Enterprise social</td>
</tr>
<tr>
<td>Mighty Networks</td>
<td>$99/month</td>
<td>Cloud SaaS</td>
<td>Yes (partial white-label)</td>
<td>Yes</td>
<td>Partial</td>
<td>Courses + community</td>
</tr>
<tr>
<td>Disciple.media</td>
<td>$59+/month</td>
<td>Cloud SaaS</td>
<td>Yes</td>
<td>Yes</td>
<td>Full</td>
<td>Creator communities</td>
</tr>
</tbody>
</table>

<h2>ShaunSocial: Best White Label Social Media Platform Overall</h2>
<p>ShaunSocial is the top choice in 2026 because it is the only platform offering a fully native iOS and Android mobile app as part of a self-hosted, one-time-price white-label package. The feature set is comprehensive and production-ready: news feed, user profiles, groups, pages, events, marketplace, live streaming, real-time messaging, push notifications, multi-language support, and a full admin panel for managing users, content, and settings. The white-label depth is total — you remove all ShaunSocial branding, configure your own domain, upload your logo, apply your color scheme, and publish the mobile apps under your own brand name and developer account in the App Store and Google Play. The full PHP source code is included with the license, which means unlimited customization: your developers can add features, modify layouts, and integrate third-party APIs without restriction. Critically, ShaunSocial is a one-time purchase — you pay once and own the software forever, with no monthly or annual SaaS fees eating into your operating budget. For a platform comparison with other options in the broader ecosystem, see our guide to <a href="https://shaunsocial.com/best-social-network-softwares-in-2025-comparison/">best social network software</a>.</p>
<ul>
<li><strong>Pros:</strong> Native iOS and Android app publishable to App Store and Google Play under your brand, one-time cost with no recurring SaaS fees, full PHP source code included, complete white-labeling across all surfaces, active development with regular updates.</li>
<li><strong>Cons:</strong> Requires self-hosting setup (server configuration, domain DNS, SSL), which demands basic technical knowledge or a developer.</li>
</ul>
<p><strong>Price:</strong> One-time license from <a href="https://shaunsocial.com">shaunsocial.com</a>. <strong>Demo:</strong> <a href="https://shaunsocial.com/demo/">https://shaunsocial.com/demo/</a></p>

<h2>Bettermode: Best Cloud-Based White Label Community Platform</h2>
<p>Bettermode, formerly known as Tribe, is a cloud SaaS community platform that has grown into one of the most polished managed options in the market, starting at $499/month. It is particularly strong for B2B customer communities, offering a modern and clean UI, an extensive integration ecosystem (Slack, Zapier, HubSpot, Salesforce, and hundreds of others via API), and flexible space types that let you mix discussion boards, Q&amp;A, idea portals, and knowledge bases in a single community. White-labeling is complete on the user-facing side — your brand, domain, and colors are all that users see. However, Bettermode does not offer a native mobile app; members access the community through a Progressive Web App (PWA) in their mobile browser. There is no source code access, and you are entirely dependent on Bettermode's infrastructure and roadmap. For businesses with a $500+/month budget that want managed hosting and first-class integrations without any technical setup, Bettermode is the leading SaaS choice.</p>
<ul>
<li><strong>Pros:</strong> Fully managed hosting with no technical maintenance, modern and intuitive UI, excellent integration ecosystem, no server setup required.</li>
<li><strong>Cons:</strong> Expensive monthly fees ($499+/month = $5,988+/year), no native mobile app (PWA only), no source code access, significant vendor lock-in.</li>
</ul>

<h2>Hivebrite: Best for Alumni and Association Communities</h2>
<p>Hivebrite is purpose-built for alumni networks, professional associations, and membership organizations, starting at $500+/month depending on community size and features required. The platform includes features that are specifically designed for this niche: member directories with advanced search and filtering, event management with ticketing and RSVPs, donation collection tools, job boards, mentorship matching, and deep CRM integrations with Salesforce and other systems that associations commonly use. The reporting and analytics suite is strong for understanding member engagement trends over time. White-labeling is complete for the user-facing experience. However, Hivebrite's association-specific design means it is a poor fit for general-purpose social networks or brand communities that do not need alumni-style features. Mobile access is PWA only, and the pricing makes it inaccessible for smaller organizations. If you are considering alternatives in this category, our comparison of <a href="https://shaunsocial.com/best-wowonder-alternative-2026/">WoWonder alternatives</a> covers several platforms that Hivebrite competes with.</p>
<ul>
<li><strong>Pros:</strong> Purpose-built association features (member directory, donations, job boards, mentorship), strong CRM integrations, excellent event management tooling.</li>
<li><strong>Cons:</strong> Very expensive for what it offers, niche use case (poor fit outside alumni/associations), no native mobile app, limited customization flexibility outside its intended vertical.</li>
</ul>

<h2>HumHub: Best Open Source White Label Community Platform</h2>
<p>HumHub is the leading open-source option in the white-label social platform category. The free community edition is released under the LGPL/MIT license and includes a solid core of social features: an activity stream, user profiles, private groups, direct messaging, file sharing, and a modular extension system with dozens of community-built modules available on the HumHub marketplace. It is self-hosted on your own PHP/MySQL server, giving you complete data ownership and control. The enterprise edition, priced at €599+/year, adds LDAP/Active Directory integration, advanced modules, priority support, and additional compliance features useful for corporate deployments. HumHub has an active GitHub community with regular updates and a responsive core development team. The platform does not offer a native mobile app — mobile access is via a PWA in the browser. Setup requires comfort with PHP server administration. For developers interested in the underlying architecture, our overview of <a href="https://shaunsocial.com/best-frameworks-to-create-a-social-network-in-2025/">frameworks to build a social network</a> provides useful technical context.</p>
<ul>
<li><strong>Pros:</strong> Free community edition with no licensing cost, open source with full code access, active developer community, well-designed module system for extending functionality, complete data control via self-hosting.</li>
<li><strong>Cons:</strong> No native mobile app (PWA only), requires technical server setup and ongoing maintenance, limited commercial features in the free tier.</li>
</ul>

<h2>phpFox: Established White Label Social Platform</h2>
<p>phpFox has been a social network script since 2005, making it one of the oldest and most established platforms in this space. It operates on a subscription model at $149/month, which is significantly cheaper than enterprise SaaS options but adds up to $1,788/year — more than its competitors at this tier over a multi-year horizon. phpFox is self-hosted PHP software with a large plugin and theme marketplace that has accumulated hundreds of add-ons over nearly two decades of operation. The documentation is extensive, community forums are active, and the plugin ecosystem means many common features can be added without custom development. However, phpFox has not kept pace with modern UI trends — the interface can feel dated compared to newer platforms like ShaunSocial or Bettermode — and there is no native mobile app offering. Its best use case is communities that need a proven, stable platform with a rich add-on ecosystem and are not concerned with cutting-edge UI or mobile app presence.</p>
<ul>
<li><strong>Pros:</strong> Two decades of proven stability, large plugin and theme marketplace, thorough documentation, self-hosted with full data control.</li>
<li><strong>Cons:</strong> Monthly subscription fees add up over time, no native mobile app, dated UI that lags behind modern design standards, slower innovation pace compared to newer entrants.</li>
</ul>

<h2>SocialEngine: Enterprise White Label Social Network</h2>
<p>SocialEngine has served enterprise clients since 2007 and remains a respected name in the corporate social network space. Annual licensing starts at $299+ depending on the edition selected. Like phpFox, SocialEngine is built on PHP and is self-hosted, with a plugin marketplace containing hundreds of commercial and free add-ons. Its enterprise credentials are strong: the platform has powered internal social networks and public community sites for large organizations across finance, healthcare, media, and government sectors. The admin tools are mature, with granular role-based permissions, content moderation workflows, and compliance-oriented features. White-labeling is complete — your brand is fully in control. The primary weaknesses are the lack of native mobile apps and a technology stack and development pace that has not kept up with modern frameworks. For enterprises with strict compliance and governance requirements that need an established platform rather than a newer entrant, SocialEngine remains a viable choice. Understanding the full landscape of <a href="https://shaunsocial.com/social-cms-what-it-is-features-and-top-platforms-in-2026/">social CMS</a> platforms can help contextualize where SocialEngine fits in the broader market.</p>
<ul>
<li><strong>Pros:</strong> Enterprise-grade maturity and stability, large plugin library, long track record in compliance-sensitive industries, self-hosted with full data control.</li>
<li><strong>Cons:</strong> Annual fees, no native mobile app, aging technology stack, slow innovation cycle compared to modern competitors.</li>
</ul>

<h2>Mighty Networks: Course + Community Hybrid Platform</h2>
<p>Mighty Networks takes a different approach from the other platforms in this list — it is primarily a creator platform that combines online course delivery with community features, starting at $99/month. It does offer native mobile apps for iOS and Android, which sets it apart from several competitors. However, white-labeling on Mighty Networks is partial rather than complete: while your members see your brand prominently, Mighty Networks branding may appear in certain flows — particularly in the mobile app store listing and some backend processes — depending on your subscription tier. The platform is well-suited for educators, coaches, and content creators who want to sell online courses and build a community around their content, with features like paid memberships, content gating, and live events. It is not designed to be a general-purpose social network for businesses or brands. The cloud-only model means no data portability or self-hosting option.</p>
<ul>
<li><strong>Pros:</strong> Native iOS and Android app available, integrated course and community features, good monetization tools for creators, relatively affordable entry-level pricing.</li>
<li><strong>Cons:</strong> Partial white-labeling (Mighty Networks branding visible in some contexts), cloud only with no self-hosting option, not suitable for general social networks, limited customization for non-creator use cases.</li>
</ul>

<h2>Disciple.media: Best for Creator Communities</h2>
<p>Disciple.media (now branded simply as Disciple) focuses on creator-led and brand-led community building, with pricing starting at $59/month for the basic tier. The platform includes a white-labeled native mobile app for iOS and Android that is published under your brand — a significant advantage over purely web-based competitors at this price point. Cloud hosted with no self-hosting option. The feature set is designed around creator monetization: paid membership tiers, exclusive content sections, live audio rooms, and in-app purchases. For established brands building a community around their product, or for content creators building a paid membership community, Disciple offers a strong combination of mobile presence and monetization tools at a lower price point than Bettermode. The trade-off is a smaller feature set than ShaunSocial for general social networking use cases, and the SaaS model means ongoing monthly costs and no data portability.</p>
<ul>
<li><strong>Pros:</strong> White-labeled native mobile app included, good monetization features for creators, relatively affordable at $59/month entry, professional user interface.</li>
<li><strong>Cons:</strong> Cloud only (no self-hosting), less feature-complete than ShaunSocial for general social networking, smaller overall feature set, ongoing monthly cost.</li>
</ul>

<h2>What Is the Best White Label Community Platform in 2026?</h2>
<p>The term "community platform" describes a specific set of features focused on member interaction, connection, and engagement rather than one-way content broadcasting. A true white label community platform should include: a searchable member directory that enables discovery and connection between members, threaded discussion forums or topic channels, private and public groups with their own feeds, an events calendar with RSVP management, member badges and gamification mechanics (points, levels, leaderboards) that encourage ongoing participation, direct messaging between members, email notification digests for activity summaries, and comprehensive admin moderation tools including content flagging, user banning, and spam controls. Not every platform in this roundup delivers all of these community-specific features equally well.</p>
<p>For community functionality specifically, the top three choices in 2026 are ShaunSocial, HumHub, and Bettermode. <strong>ShaunSocial</strong> is the best overall white label community platform because it covers every community feature — groups, events, member profiles, messaging, notifications — plus adds features that pure community platforms often lack, such as marketplace, live streaming, and a native mobile app. Members can discover each other through profiles, connect via groups based on interests, and engage through the main feed or group feeds, all under your brand. <strong>HumHub</strong> is the best free and open-source community platform, with a particularly strong module system that lets you add specialized community features (polls, calendars, wiki) from the marketplace without custom development. The core activity stream and group system are well-designed. <strong>Bettermode</strong> is the best managed SaaS community platform, particularly for B2B customer communities where integrations with CRM and support tools matter more than native mobile apps. When evaluating community platforms, also consider member discovery design (how easily can members find each other?), group management and moderation workflow, and the quality of email notification design — these details significantly affect long-term member retention and engagement.</p>

<h2>Best White Label Social Media App in 2026</h2>
<p>When people search for a white label social media app, they are usually asking a specific question: can I get a mobile app in the App Store and Google Play that carries my brand? The answer depends on which platform you choose, and the difference between native apps and PWAs is consequential enough to warrant detailed explanation.</p>
<p>A <strong>native app</strong> (iOS/Android) is a dedicated application built for each mobile operating system, distributed through the Apple App Store and Google Play Store. Users search for and install your app by name — your brand name, not the vendor's. Native apps support full push notifications (with significantly higher delivery and open rates than web push), offline functionality, camera and microphone integrations, and the performance characteristics that users expect from a premium mobile experience. Critically, having an app in the app stores builds substantial user trust — users recognize that being in the App Store or Google Play means the app has passed a review process. <strong>Progressive Web Apps (PWAs)</strong> run in the mobile browser and can be "added to home screen" to simulate an app icon, but they are not listed in the App Store or Google Play, have more limited push notification support, and are generally perceived as less trustworthy by users unfamiliar with the distinction.</p>
<p>Among white-label platforms in 2026, only three offer genuine native mobile apps: <strong>ShaunSocial</strong> provides fully native iOS and Android apps that you publish to the App Store and Google Play under your own developer account and brand name, with full push notification support — this is the only self-hosted platform to offer this capability. <strong>Disciple.media</strong> also offers a white-labeled native mobile app, though at ongoing monthly SaaS cost. <strong>Mighty Networks</strong> provides mobile apps, but white-labeling is partial. All other major platforms — Bettermode, HumHub, phpFox, and SocialEngine — use PWA only, which cannot be listed in app stores and typically see lower engagement than native alternatives. The research on native vs. PWA engagement consistently shows higher retention, higher push notification opt-in rates, and more daily active usage for native apps, making this a critical differentiator for platforms expecting significant mobile usage.</p>

<h2>How to Choose the Right White Label Social Media Platform</h2>
<p>With eight strong options across very different architectures and price points, choosing the right white-label social media platform requires a structured approach. Use the following decision framework to narrow your options:</p>
<p><strong>Self-hosted vs. SaaS:</strong> Self-hosted platforms (ShaunSocial, HumHub, phpFox, SocialEngine) run on your own server. You control all data, there is no vendor lock-in, and the cost is typically a one-time purchase or lower annual fee. The trade-off is that you are responsible for server setup, security updates, backups, and performance scaling. SaaS platforms (Bettermode, Hivebrite, Disciple) are fully managed — you pay a higher monthly fee but have no infrastructure responsibility. For most non-technical teams, SaaS is operationally simpler; for teams with technical resources or strong data governance requirements, self-hosted is preferable.</p>
<p><strong>Budget considerations:</strong> If your budget is under $500 total, HumHub's free community edition on a $5-20/month VPS is the only realistic option. If you have a one-time budget of $1,500-3,000 and want a full-featured platform with a native mobile app, ShaunSocial at $2,499 one-time is the clear winner — it costs less than five months of Bettermode. If your budget is $500-1,000/month and you need managed SaaS, Bettermode is the best choice. If your budget exceeds $1,000/month and you serve an alumni or association audience, Hivebrite is worth evaluating.</p>
<p><strong>Mobile app requirement:</strong> If you need a native iOS and Android app in the app stores under your brand, ShaunSocial is the only self-hosted option that delivers this. Disciple.media also offers white-labeled native apps at $59+/month ongoing. If a PWA is acceptable, all platforms are viable.</p>
<p><strong>Open source requirement:</strong> If your organization requires open-source code (for compliance, security auditing, or modification rights), HumHub is the only major option. ShaunSocial includes full PHP source code but under a commercial license, not an open-source license.</p>
<p><strong>Use case alignment:</strong> Alumni and professional associations → Hivebrite. Creator monetization with courses → Mighty Networks or Disciple. Open-source community with developer control → HumHub. General-purpose branded social network for a business, brand, or customer community → ShaunSocial. Enterprise with extensive plugin requirements → phpFox or SocialEngine.</p>"""

faq_html = """<div class="faq-item"><h3>What is a white label social media platform?</h3><p>A white-label social media platform is software that you license and brand entirely as your own, with no vendor logos or branding visible to your users. You use your own domain name, logo, colors, and app name. Key characteristics include: custom domain, full brand control, no vendor watermarks, and modular features. Unlike open-source software (which is about code licensing), white-labeling is specifically about branding — you can have a white-label platform that is not open source.</p></div>
<div class="faq-item"><h3>Which white label social media platform has the best mobile app?</h3><p>ShaunSocial is the only major white-label social media platform offering fully native iOS and Android apps that you can publish to the App Store and Google Play under your own brand name. All other platforms in this category (Bettermode, HumHub, phpFox, SocialEngine) offer only Progressive Web Apps (PWAs), which cannot be listed in app stores and have lower user engagement than native apps. Disciple.media also offers a white-labeled mobile app but at higher ongoing cost.</p></div>
<div class="faq-item"><h3>Is ShaunSocial a white label platform?</h3><p>Yes, ShaunSocial is a fully white-label social media platform. You can remove all ShaunSocial branding, use your own domain name, customize colors and logos, and publish the included iOS and Android apps under your own brand name in the App Store and Google Play. The full PHP source code is included, so you can customize every aspect of the platform. There are no visible ShaunSocial watermarks or branding on the end-user interface.</p></div>
<div class="faq-item"><h3>What is the cheapest white label community platform?</h3><p>HumHub is the cheapest white label community platform — the community edition is free and open source. It requires self-hosting on your own server (typically $5-20/month on a VPS). For a more feature-complete option, ShaunSocial costs $2,499 as a one-time license with no ongoing fees, making it extremely cost-effective compared to SaaS alternatives like Bettermode ($499/month = $5,988/year) or Hivebrite ($500+/month = $6,000+/year).</p></div>
<div class="faq-item"><h3>Can I use my own domain with a white label social platform?</h3><p>Yes, all white-label social media platforms support custom domains. With self-hosted options like ShaunSocial, HumHub, and phpFox, you point your domain's DNS to your server and configure it during setup — your community lives entirely at your domain. With SaaS platforms like Bettermode and Disciple.media, you configure a CNAME record to point your domain to their servers. In both cases, users only ever see your domain, never the vendor's.</p></div>
<div class="faq-item"><h3>What is the difference between white label and open source social software?</h3><p>White label refers to branding: a white-label platform lets you remove vendor branding and present the software as your own product. Open source refers to code licensing: open-source software gives you access to the source code and the right to modify and distribute it. These concepts are independent — ShaunSocial is white-label but not open source (proprietary code, commercial license). HumHub is both white-label and open source. phpFox is white-label but proprietary. You can have white-label without open source, or open source without white-label.</p></div>"""

# Count words in body_html
import re
word_count = len(re.findall(r'\b\w+\b', re.sub(r'<[^>]+>', ' ', body_html)))
print(f"Body HTML word count: {word_count}")

site = get_site(4)
wp_url = site['wp_url'].rstrip('/')
auth = (site['wp_username'], site['wp_app_password'])
final_html = assemble_final_html(site=site,
    title="Best White Label Social Media Platform in 2026 (Ranked & Compared)",
    tldr="ShaunSocial is the best white-label social media platform in 2026, offering native iOS and Android apps, full brand control, and a one-time purchase price. For open-source, HumHub is the top free choice. For managed SaaS, Bettermode leads the field. This guide ranks and compares all 8 major platforms.",
    content=body_html, faq=faq_html,
    meta_description="Compare the 8 best white label social media platforms in 2026: ShaunSocial, Bettermode, HumHub & more. Find the right white label community platform.",
    meta_title="Best White Label Social Media Platform in 2026",
    cta_link="https://shaunsocial.com/demo/", cta_text="Try ShaunSocial Free Demo")
json_ld = _build_json_ld("Best White Label Social Media Platform in 2026 (Ranked & Compared)", "Article",
    "Compare the 8 best white label social media platforms in 2026: ShaunSocial, Bettermode, HumHub & more.", faq_html)
full_content = json_ld + "\n" + final_html
resp = requests.post(f"{wp_url}/wp-json/wp/v2/posts/3536",
    json={"title": "Best White Label Social Media Platform in 2026 (Ranked & Compared)", "content": full_content, "status": "publish"},
    auth=auth, headers={"Content-Type": "application/json"}, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code in (200, 201):
    _xmlrpc_set_yoast_meta(wp_url, site['wp_username'], site['wp_app_password'], 3536, {
        "_yoast_wpseo_metadesc": "Compare the 8 best white label social media platforms in 2026: ShaunSocial, Bettermode, HumHub & more. Find the right white label community platform.",
        "_yoast_wpseo_focuskw": "white label social media platform",
        "_yoast_wpseo_title": "Best White Label Social Media Platform in 2026 %%sep%% %%sitename%%",
    })
    print("Done")
else:
    print(f"Error: {resp.text[:500]}")
