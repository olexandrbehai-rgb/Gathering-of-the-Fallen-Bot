const rawTracks = [
  ["Блукаючий козак", ["emigrant", "nostalgia"]],
  ["Полум'я (FLAMME)", ["fire", "strength"]],
  ["Полум'я серця", ["fire"]],
  ["Валькірія Димуйгоря", ["fire", "strength"]],
  ["Із Попелу", ["strength", "fire"]],
  ["Through the Ashes", ["strength", "fire"]],
  ["Гори", ["strength"]],
  ["Залізний Спадок", ["strength"]],
  ["Легіон", ["strength"]],
  ["Темний Політ", ["strength"]],
  ["Кобзар", ["strength", "nostalgia"]],
  ["Дід Максим", ["strength"]],
  ["Samurai", ["fire", "strength"]],
  ["Не втрачай", ["fire", "strength"]],
  ["Живи!!!", ["fire", "strength"]],
  ["Вогонь В Руках", ["fire"]],
  ["Палаючі серця", ["fire"]],
  ["Shadows Beneath the Flame", ["fire"]],
  ["Попіл і Воля", ["strength"]],
  ["У Танці із Попелом", ["strength"]],
  ["Крізь уламки і Дим", ["strength"]],
  ["Реквієм Народу", ["nostalgia"]],
  ["Псалми", ["nostalgia"]],
  ["Молодість", ["nostalgia"]],
  ["Я виріс на акордах", ["nostalgia"]],
  ["Старий Хорон", ["nostalgia"]],
  ["Чорна Береза", ["nostalgia"]],
  ["Гілка Бузку", ["nostalgia"]],
  ["Зацвіли Яблуні", ["nostalgia"]],
  ["Жовті Ліхтарі", ["nostalgia"]],
  ["Тихі кроки", ["nostalgia"]],
  ["Скрипаль", ["nostalgia"]],
  ["Заграй мені трішки", ["nostalgia"]],
  ["Тетянин Блюз", ["nostalgia"]],
  ["Подруга стара", ["nostalgia"]],
  ["Піду я до Саду", ["nostalgia"]],
  ["Ой, розлився степ широкий", ["nostalgia"]],
  ["Ой, у лузі вітер виє", ["nostalgia"]],
  ["Орися (кавер)", ["nostalgia"]],
  ["Ти вже не той", ["nostalgia"]],
  ["Пустка", ["nostalgia"]],
  ["Пустеля Душ", ["nostalgia", "emigrant"]],
  ["У Темряві Серця", ["nostalgia"]],
  ["Wings of the Eternal Night", ["nostalgia"]],
  ["Ashes Whispering", ["nostalgia"]],
  ["Shadows of the Past", ["nostalgia"]],
  ["Shadows of Yesterday", ["nostalgia"]],
  ["Echoes of the Fallen", ["nostalgia"]],
  ["White Dove", ["nostalgia"]],
  ["In Memory Of Diesel", ["nostalgia"]],
  ["Only She (Лиш Вона)", ["nostalgia"]],
  ["Хіба у тому вся вина", ["nostalgia"]],
  ["Емігрант", ["emigrant", "nostalgia"]],
  ["Вигнаний ангел", ["emigrant"]],
  ["Несу", ["emigrant"]],
  ["Подорож Довжиною в Життя", ["emigrant"]],
  ["Road Through The Sand", ["emigrant"]],
  ["To Bring You Back", ["emigrant"]],
  ["Я прийшла щоб торкнутися серця", ["nostalgia"]],
  ["Крізь тіні і час", ["nostalgia"]],
  ["Life (Життя)", ["fire"]],
  ["If You Want", ["fire"]],
  ["Рагга душі Хард", ["fire"]],
  ["Різдвяна Рок Опера", ["fire"]],
] as const;

const youtubeSearch = (title: string) =>
  `https://www.youtube.com/results?search_query=${encodeURIComponent(`Gathering Of The Fallen ${title}`)}`;
const musicSearch = (service: "spotify" | "apple", title: string) => {
  const query = encodeURIComponent(`Gathering Of The Fallen ${title}`);
  return service === "spotify"
    ? `https://open.spotify.com/search/${query}`
    : `https://music.apple.com/search?term=${query}`;
};

const legacyTracks = rawTracks.map(([title, moods], index) => ({
  id: String(index + 1),
  title,
  moods: [...moods],
  youtubeUrl:
    title === "Гори"
      ? "https://www.youtube.com/watch?v=ZwNsc0A6mD8"
      : youtubeSearch(title),
  youtubeMusicUrl: `https://music.youtube.com/search?q=${encodeURIComponent(`Gathering Of The Fallen ${title}`)}`,
  spotifyUrl: musicSearch("spotify", title),
  appleMusicUrl: musicSearch("apple", title),
}));

export const releases = [
  {
    id: "music-of-my-soul",
    title: "Music Of My Soul",
    description: "21 композиція про пам’ять, силу, вигнання та повернення до себе.",
    date: "2025",
    url: "https://music.youtube.com/@gathering_of_the_fallen",
    accent: "album",
  },
  {
    id: "gory",
    title: "Гори",
    description: "Маніфест сили — для тих, хто проходить крізь попіл і не зникає.",
    date: "2026",
    url: "https://www.youtube.com/watch?v=ZwNsc0A6mD8",
    accent: "single",
  },
  {
    id: "new-era",
    title: "Нова ера",
    description: "Серія нових композицій про еміграцію, пам’ять і незламність.",
    date: "2026",
    url: "https://www.youtube.com/@gathering_of_the_fallen",
    accent: "coming",
  },
];

const officialVideos = [
  ["eBgXAXDKgDk", "Додому (за участі Olia Stefaniw)", "3:56"],
  ["_C1h2jO0bRw", "Два Кольори", "3:53"],
  ["CBr2Y310uis", "ХУ ЕМ АЙ?", "3:34"],
  ["h_fzp76UyU4", "Свій Харон (за участі SOLOMIYA_UA)", "5:43"],
  ["xvcfd7hEnN0", "Розкажи-но ти про себе", "5:10"],
  ["3LMjpBT2Ga0", "Доки крутяться колеса", "4:37"],
  ["T87SfKuDqWw", "Повільніше за ніч", "5:25"],
  ["O3YQfGqRvmc", "Я ще Тут!!!", "4:28"],
  ["vhOB--QHPyY", "Ти прийшла, щоб торкнутися серця!", "5:18"],
  ["5OBgxk5ZZYM", "Дівчина у Чорній сукні", "5:21"],
  ["JCxLAUHZnKY", "Скажи небу, що ми Були...", "5:41"],
  ["-239_7s10oM", "Голосніше За Грім", "6:01"],
  ["Pq311kM-pvA", "Горіла Земля", "7:12"],
  ["e8_fwfez7e0", "Боги Грому", "6:08"],
  ["zy3Uz86MLxo", "Дикі Дзвони", "4:14"],
  ["Orq96rW4n4c", "Вогонь під Дощем", "4:27"],
  ["aqOD3RmJsOY", "Не Озирайся", "4:01"],
  ["lWez4Iu1ucE", "Війна із самим Собою", "4:45"],
  ["yk5XB8SqKE8", "Храм Очей", "3:55"],
  ["UyypaV0yY8g", "Горіла Сосна (кавер)", "3:04"],
  ["Sp43M8nz1RA", "Лист До Самого Себе", "3:11"],
  ["-8VTIAA8GLQ", "Козак Крізь Віки", "4:28"],
  ["O-uzMQfY-KI", "Підіймай Вогонь", "4:02"],
  ["8CjKQohRQwQ", "Чуже Лице", "4:07"],
  ["jnp7IErWCDs", "Нічний Снайпер", "4:37"],
  ["NU1SSEoijIk", "Бас і Дим", "4:12"],
  ["q2fmSRDy8QU", "Блукаючий Козак", "4:22"],
  ["sm4yVIlE0Oc", "Псалми", "4:39"],
  ["2AkrCvzU4Ss", "Wings of the Eternal Night", "4:40"],
  ["2Q2THoiQfLA", "Не втрачай", "3:54"],
] as const;

export const videos = officialVideos.map(([id, title, duration]) => ({
  id,
  title,
  duration,
  youtubeUrl: `https://www.youtube.com/watch?v=${id}`,
  youtubeMusicUrl: `https://music.youtube.com/watch?v=${id}`,
  thumbnailUrl: `https://i.ytimg.com/vi/${id}/hqdefault.jpg`,
}));

const normalizeTitle = (title: string) =>
  title.toLocaleLowerCase("uk-UA").replace(/[’ʼ`]/g, "'").trim();
const officialTitles = new Set(videos.map((video) => normalizeTitle(video.title)));

export const tracks = [
  ...videos.map((video, index) => ({
    id: `official-${index + 1}`,
    title: video.title,
    moods: ["strength"],
    youtubeUrl: video.youtubeUrl,
    youtubeMusicUrl: video.youtubeMusicUrl,
    spotifyUrl: musicSearch("spotify", video.title),
    appleMusicUrl: musicSearch("apple", video.title),
  })),
  ...legacyTracks
    .filter((track) => !officialTitles.has(normalizeTitle(track.title)))
    .map((track) => ({ ...track, id: `legacy-${track.id}` })),
];