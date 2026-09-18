---
title: 'Your Post Title'
date: '{{DATE}}'
author: 'Joey French'
site: '{{SITE}}'
excerpt: 'One or two sentences that summarize the post — used in listings and as the SEO description fallback.'
metaDescription: 'A focused ~150-160 character description for search engines. Falls back to the excerpt if omitted.'
tags: ['tag-one', 'tag-two']
keywords: ['keyword one', 'keyword two', 'keyword three']
canonicalUrl: 'https://{{DOMAIN}}/blog/{{SLUG}}'
---

Open with the idea. The first paragraph or two should stand on their own — they become the
preview and set up everything that follows.

## A section heading

Write the body in Markdown. Headings, lists, links, and code blocks all render in the app.
When you run `just blog-narrate {{SLUG}}`, code blocks and tables are stripped and the rest is
read aloud, so keep prose self-contained and avoid relying on a table to carry the argument.

- Bullets are fine
- They are unwrapped for narration

Link out before you close. A lesson in a series links the lesson before it. When this one
ships, edit that earlier lesson to link forward to it. Every post also links one product page
on its own site: the homepage, or a page such as /platform, /pricing or /docs. A post that links
nowhere is a dead end for readers and crawlers alike.

Close with the takeaway.
