/**
 * Seed script: insert all titles into the database.
 * Run with: npm run db:seed
 */

import { PrismaClient } from "@prisma/client";
import { TITLES } from "@/lib/titles";

const prisma = new PrismaClient();

async function seed() {
  console.log("Seeding titles...");

  for (const t of TITLES) {
    const result = await prisma.title.upsert({
      where: { slug: t.slug },
      update: {
        name: t.name,
        steamAppId: t.steamAppId,
        subreddit: t.subreddit,
        genreTags: [t.genre],
        steamShare: t.steamShare,
      },
      create: {
        name: t.name,
        slug: t.slug,
        steamAppId: t.steamAppId,
        subreddit: t.subreddit,
        genreTags: [t.genre],
        steamShare: t.steamShare,
      },
    });
    console.log(`  ${result.name} (id: ${result.id})`);
  }

  console.log(`Done. ${TITLES.length} titles seeded.`);
  await prisma.$disconnect();
}

seed().catch(console.error);
