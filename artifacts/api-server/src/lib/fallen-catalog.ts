import catalogData from "../../../../catalog/fallen-catalog.json";

type Mood = "nostalgia" | "strength" | "fire" | "emigrant";
type Links = Record<string, string>;
type CatalogTrack = { title: string; moods: Mood[]; links?: Links };
type CatalogVideo = CatalogTrack & {
  videoId: string;
  duration: string;
};
type CatalogRelease = {
  id: string;
  title: string;
  description: string;
  date: string;
  url: string;
  accent: string;
};
type Catalog = {
  bandName: string;
  moods: Record<Mood, string>;
  tracks: CatalogTrack[];
  videos: CatalogVideo[];
  releases: CatalogRelease[];
};

const normalizeTitle = (title: string) =>
  title.toLocaleLowerCase("uk-UA").replace(/[’ʼ`]/g, "'").trim();

function validateCatalog(value: unknown): Catalog {
  if (!value || typeof value !== "object") {
    throw new Error("The shared music catalog must be an object.");
  }
  const catalog = value as Partial<Catalog>;
  if (
    !catalog.moods ||
    !Array.isArray(catalog.tracks) ||
    !Array.isArray(catalog.videos) ||
    !Array.isArray(catalog.releases)
  ) {
    throw new Error("The shared music catalog is missing required sections.");
  }

  const allowedMoods = new Set(Object.keys(catalog.moods));
  const titles = new Set<string>();
  const validateItems = (items: CatalogTrack[]) => {
    for (const item of items) {
      const title = typeof item.title === "string" ? normalizeTitle(item.title) : "";
      if (!title || titles.has(title)) {
        throw new Error(`Invalid or duplicate catalog title: ${item.title}`);
      }
      titles.add(title);
      if (
        !Array.isArray(item.moods) ||
        item.moods.length === 0 ||
        item.moods.some((mood) => !allowedMoods.has(mood))
      ) {
        throw new Error(`Invalid moods for catalog title: ${item.title}`);
      }
      if (
        item.links &&
        Object.values(item.links).some(
          (url) => typeof url !== "string" || !url.startsWith("https://"),
        )
      ) {
        throw new Error(`Invalid link for catalog title: ${item.title}`);
      }
    }
  };
  validateItems(catalog.tracks);
  validateItems(catalog.videos);

  const videoIds = new Set<string>();
  for (const video of catalog.videos) {
    if (!video.videoId || videoIds.has(video.videoId)) {
      throw new Error(`Invalid or duplicate videoId: ${video.videoId}`);
    }
    videoIds.add(video.videoId);
  }

  const releaseIds = new Set<string>();
  for (const release of catalog.releases) {
    if (
      !release.id ||
      releaseIds.has(release.id) ||
      !release.title ||
      !release.description ||
      !release.date ||
      !release.url?.startsWith("https://") ||
      !release.accent
    ) {
      throw new Error(`Invalid or duplicate release: ${release.id}`);
    }
    releaseIds.add(release.id);
  }
  return catalog as Catalog;
}

const catalog = validateCatalog(catalogData);

const youtubeSearch = (title: string) =>
  `https://www.youtube.com/results?search_query=${encodeURIComponent(`${catalog.bandName} ${title}`)}`;
const musicSearch = (service: "spotify" | "apple", title: string) => {
  const query = encodeURIComponent(`${catalog.bandName} ${title}`);
  return service === "spotify"
    ? `https://open.spotify.com/search/${query}`
    : `https://music.apple.com/search?term=${query}`;
};

export const releases = catalog.releases;

export const videos = catalog.videos.map((video) => ({
  id: video.videoId,
  title: video.title,
  duration: video.duration,
  youtubeUrl: `https://www.youtube.com/watch?v=${video.videoId}`,
  youtubeMusicUrl: `https://music.youtube.com/watch?v=${video.videoId}`,
  thumbnailUrl: `https://i.ytimg.com/vi/${video.videoId}/hqdefault.jpg`,
}));

export const tracks = [
  ...catalog.videos.map((video, index) => ({
    id: `official-${index + 1}`,
    title: video.title,
    moods: video.moods,
    youtubeUrl:
      video.links?.YouTube ??
      `https://www.youtube.com/watch?v=${video.videoId}`,
    youtubeMusicUrl:
      video.links?.["YouTube Music"] ??
      `https://music.youtube.com/watch?v=${video.videoId}`,
    spotifyUrl:
      video.links?.Spotify ?? musicSearch("spotify", video.title),
    appleMusicUrl:
      video.links?.["Apple Music"] ?? musicSearch("apple", video.title),
  })),
  ...catalog.tracks.map((track, index) => ({
    id: `legacy-${index + 1}`,
    title: track.title,
    moods: track.moods,
    youtubeUrl: track.links?.YouTube ?? youtubeSearch(track.title),
    youtubeMusicUrl:
      track.links?.["YouTube Music"] ??
      `https://music.youtube.com/search?q=${encodeURIComponent(`${catalog.bandName} ${track.title}`)}`,
    spotifyUrl:
      track.links?.Spotify ?? musicSearch("spotify", track.title),
    appleMusicUrl:
      track.links?.["Apple Music"] ?? musicSearch("apple", track.title),
  })),
];