import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Link fields are rendered straight into href attributes. z.string().url()
// alone is not enough: "javascript:alert(1)" and "data:..." parse as valid
// URLs and would execute on click. Restrict to http(s) so hostile schemes
// are rejected at build time.
const httpUrl = z.union([
  z.literal(''),
  z
    .string()
    .url()
    .refine((value) => /^https?:\/\//i.test(value), {
      message: 'URL must use the http or https scheme'
    })
]);

const research = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/research' }),
  schema: z.object({
    title: z.string(),
    subtitle: z.string().optional(),
    authors: z.array(z.string()),
    status: z.enum([
      'published',
      'preprint',
      'technical-note',
      'expository-note',
      'work-in-progress',
      'notebook-entry'
    ]),
    venue: z.string().optional(),
    date: z.date(),
    updatedDate: z.date().optional(),
    version: z.string().optional(),
    summary: z.string(),
    abstract: z.string(),
    contributions: z.array(z.string()).default([]),
    limitations: z.array(z.string()).default([]),
    related: z.array(z.string()).default([]),
    arxivId: z.string().regex(/^[0-9]{4}\.[0-9]{4,5}(v[0-9]+)?$/).optional(),
    pdfUrl: httpUrl.optional(),
    codeUrl: httpUrl.optional(),
    bibtex: z.string().optional(),
    tags: z.array(z.string()).default([]),
    ogImage: z.string().optional(),
    draft: z.boolean().default(false)
  })
});

const projects = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/projects' }),
  schema: z.object({
    title: z.string(),
    summary: z.string(),
    date: z.date(),
    updatedDate: z.date().optional(),
    role: z.string().optional(),
    stack: z.array(z.string()).default([]),
    repoUrl: httpUrl.optional(),
    demoUrl: httpUrl.optional(),
    tags: z.array(z.string()).default([]),
    ogImage: z.string().optional(),
    draft: z.boolean().default(false)
  })
});

const notebook = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/notebook' }),
  schema: z.object({
    title: z.string(),
    date: z.date(),
    updatedDate: z.date().optional(),
    summary: z.string(),
    tags: z.array(z.string()).default([]),
    math: z.boolean().default(true),
    ogImage: z.string().optional(),
    draft: z.boolean().default(false)
  })
});

export const collections = { research, projects, notebook };
