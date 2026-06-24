---
title: 'Your Post Title'
date: '{{DATE}}'
author: 'Joey French'
excerpt: 'One or two sentences that summarize the post — used in listings and as the SEO description fallback.'
metaDescription: 'A focused ~150-160 character description for search engines. Falls back to the excerpt if omitted.'
tags: ['tag-one', 'tag-two']
keywords: ['keyword one', 'keyword two', 'keyword three']
featured: false
canonicalUrl: 'https://robosystems.ai/blog/{{SLUG}}'
---

Open with the idea. The first paragraph or two should stand on their own — they become the
preview and set up everything that follows.

## A section heading

Write the body in Markdown. Headings, lists, links, and code blocks all render in the app.
When you run `just blog-narrate {{SLUG}}`, code blocks and tables are stripped and the rest is
read aloud, so keep prose self-contained and avoid relying on a table to carry the argument.

- Bullets are fine
- They are unwrapped for narration

Close with the takeaway.
