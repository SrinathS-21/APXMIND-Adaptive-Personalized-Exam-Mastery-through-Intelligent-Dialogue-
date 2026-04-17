import { normalizeLanguage } from './language';

export type UiLanguage = 'en' | 'ta';

type TemplateVars = Record<string, string | number>;

const UI_TRANSLATIONS: Record<UiLanguage, Record<string, string>> = {
  en: {
    'app.student': 'Student',
    'app.level': 'Level {level}',
    'app.logout': 'Logout',
    'app.roleTooltip': 'Role: {role}',
    'app.selectLanguage': 'Select language',

    'nav.home': 'Home',
    'nav.ncertBooks': 'NCERT Books',
    'nav.achievements': 'Achievements',
    'nav.studyPlan': 'Study Plan',
    'nav.learnSessions': 'Learn Sessions',
    'nav.notebookStudio': 'Notebook Studio',
    'nav.resources': 'Resources',
    'nav.library': 'Library',
    'nav.notifications': 'Notifications',
    'nav.support': 'Support',
    'nav.profile': 'Profile',

    'greeting.morning': 'Good morning',
    'greeting.afternoon': 'Good afternoon',
    'greeting.evening': 'Good evening',

    'home.updated': 'Home updated successfully.',
    'home.liveRefreshFailed': 'Live home refresh failed. You are seeing local fallback values.',
    'home.retry': 'Retry',
    'home.streakMessage': 'You are on a {days}-day streak. Keep your momentum alive today.',
    'home.startStreak': 'Start a focused session now and begin your streak.',
    'home.levelXpBadge': 'Level {level} • {xp} XP',
    'home.streakChip': '{days}d streak',

    'home.xpToday': 'XP Today',
    'home.activeDays': 'Active Days',
    'home.avgFocus': 'Avg Focus',
    'home.focus': 'focus',
    'home.badges': 'Badges',

    'home.dailyTarget': 'Daily Target',
    'home.goalHours': '{hours}h goal',
    'home.studiedToday': 'Studied today',
    'home.hoursRemaining': '{hours}h remaining',
    'home.lessons': 'Lessons',
    'home.quizzes': 'Quizzes',

    'home.subjects': 'Subjects',
    'home.learn': 'Learn',
    'home.quiz': 'Quiz',
    'home.quickReferences': 'Quick References',
    'home.subject.physics.label': 'Physics',
    'home.subject.physics.description': 'Mechanics, Thermodynamics, Optics, Modern Physics',
    'home.subject.chemistry.label': 'Chemistry',
    'home.subject.chemistry.description': 'Organic, Inorganic, Physical Chemistry',
    'home.subject.biology.label': 'Biology',
    'home.subject.biology.description': 'Botany, Zoology, Genetics, Ecology',

    'home.xpToLevel': '{xp} XP to Level {level}',
    'home.badgesEarned': '{count} badges earned',
    'home.totalXp': '{xp} total XP',

    'home.week': 'Week',
    'home.month': 'Month',
    'home.year': 'Year',
    'home.previousPeriod': 'Previous period',
    'home.nextPeriod': 'Next period',
    'home.dayNumber': 'Day {day}',
    'home.activeCount': '{count} active',
    'home.loadingActivity': 'Loading {view} activity...',

    'home.nextBestActions': 'Next Best Actions',
    'home.personalizedToday': 'Personalized for today',
    'home.open': 'Open',
    'home.personalizingActions': 'Personalizing actions...',

    'home.fallback.continueLearning.title': 'Continue Learning',
    'home.fallback.continueLearning.description': 'Resume your latest chapter with one click.',
    'home.fallback.continueLearning.cta': 'Resume Chapter',
    'home.fallback.smartRevision.title': 'Smart Revision',
    'home.fallback.smartRevision.description': 'Take a short weak-area quiz to improve consistency.',
    'home.fallback.smartRevision.cta': 'Revise 15 Minutes',
    'home.fallback.planAhead.title': 'Plan Ahead',
    'home.fallback.planAhead.description': 'Set your next study block and keep your streak safe.',
    'home.fallback.planAhead.cta': 'Open Study Plan',

    'home.error.liveData': 'Unable to load live home data.',
    'home.error.nextActions': 'Unable to personalize next actions right now.',
    'home.error.heatmap': 'Unable to load period activity heatmap.',

    'books.title': 'NCERT Books',
    'books.subtitle': 'Read NCERT textbooks directly — the foundation of NEET preparation',
    'books.allSubjects': 'All Subjects',
    'books.classSubject': 'Class {classLevel} — {subject}',
    'books.chapterCount': '{count} chapters',

    'ach.title': 'Achievements',
    'ach.refreshed': 'Achievements refreshed successfully.',
    'ach.loadError': 'Unable to load achievements right now.',
    'ach.totalXp': 'Total XP',
    'ach.levelLabel': 'Level',
    'ach.currentStreak': 'Current Streak',
    'ach.badgesEarned': 'Badges Earned',
    'ach.xpToNext': '{xp} XP to next',
    'ach.bestStreak': 'Best Streak: {days} days',
    'ach.badges': 'Badges',
    'ach.earned': 'Earned {date}',

    'study.title': 'Study Plan',
    'study.daysUntilNeet': 'Days Until NEET {year}',
    'study.stayFocused': 'Stay focused, stay consistent!',
    'study.todayProgress': "Today's Progress",
    'study.studyTime': 'Study Time',
    'study.adaptivePlan': 'Adaptive Daily Plan',
    'study.refresh': 'Refresh',
    'study.generatePlan': 'Generate Plan',
    'study.loadingPlanner': 'Loading planner',
    'study.tasksCount': '{count} tasks',
    'study.minutesPlanned': '{minutes} min planned',
    'study.completedCount': '{count} completed',
    'study.pendingCount': '{count} pending',
    'study.adherence': '{percent}% adherence',
    'study.generalRevision': 'General revision',
    'study.allSubjects': 'all subjects',
    'study.minutes': 'minutes',
    'study.priority': 'priority {score}',
    'study.startMiniSet': 'Start Mini-Set',
    'study.startStamina': 'Start Stamina',
    'study.done': 'Done',
    'study.skip': 'Skip',
    'study.noPlannerTasks': 'No planner tasks available for today. Click Generate Plan to create one.',
    'study.topRiskTopics': 'Top Risk Topics',
    'study.loadingRisks': 'Loading risks',
    'study.noRiskTopics': 'No risk topics identified yet.',
    'study.calibrationWeekly': 'Calibration & Weekly Summary',
    'study.confidenceGap': 'Confidence gap',
    'study.confidentWrong': 'Confident-wrong',
    'study.retention': 'Retention',
    'study.accuracy': 'Accuracy',
    'study.speed': 'Speed',
    'study.spacedQueue': 'Spaced Revision Queue',
    'study.loadingQueue': 'Loading queue',
    'study.noDueRevisions': 'No due revision items in the next 48 hours.',
    'study.due': 'due {date}',
    'study.streak': 'streak {count}',
    'study.correct': 'Correct',
    'study.partial': 'Partial',
    'study.incorrect': 'Incorrect',
    'study.errorNotebook': 'Error Notebook',
    'study.loadingMistakes': 'Loading mistakes',
    'study.generalConcept': 'General concept',
    'study.repeatedTimes': 'repeated {count} times',
    'study.markResolved': 'Mark Resolved',
    'study.noMistakeCards': 'No active mistake cards right now.',
    'study.thisWeek': 'This Week ({days} day streak)',
    'study.heatmapNote': 'Heatmap uses live rows from /api/progress/daily with local fallback.',
    'study.logMinutes': 'Log Study Minutes',
    'study.minutesLabel': 'Minutes',
    'study.recordMinutes': 'Record Minutes',
    'study.readinessHabits': 'Readiness & Habits',
    'study.noReadiness': 'No readiness snapshot yet. Continue quizzes and revision to generate one.',
    'study.unknownRisk': 'Unknown risk',
    'study.snapshot': 'snapshot {date}',
    'study.projectedScore': 'Projected score',
    'study.coverage': 'Coverage',
    'study.consistency': 'Consistency',
    'study.focusAvg': '7d focus avg: {minutes}m/day',
    'study.sessionsPerDay': 'Sessions/day',
    'study.interruptionsPerDay': 'Interruptions/day',
    'study.mastery': 'mastery',
    'study.confidence': 'confidence',
    'study.masterySnapshot': 'Mastery Snapshot',
    'study.loadingMastery': 'Loading mastery',
    'study.noMastery': 'No mastery rows yet. Complete recalls and quizzes to populate this.',
    'study.activeRecommendations': 'Active Recommendations',
    'study.loadingRecommendations': 'Loading recommendations',
    'study.accept': 'Accept',
    'study.dismiss': 'Dismiss',
    'study.delete': 'Delete',
    'study.noRecommendations': 'No active recommendations right now. Generate a plan to refresh suggestions.',
    'study.recommendationNote': 'Recommendations are personalized from your planner, weak topics, and recent learning signals.',
    'study.suggestedRoutine': 'Suggested Daily Routine',
    'study.routine.slot1': 'Physics — Theory + NCERT reading',
    'study.routine.slot2': 'Chemistry — NCERT + practice MCQs',
    'study.routine.slot3': 'Biology — NCERT + diagrams',
    'study.routine.slot4': 'Revision — weak topics',
    'study.routine.slot5': 'Practice quizzes on APXMIND',
    'study.routine.slot6': 'PYQ solving + analysis',
    'study.routine.slot7': 'Quick revision before sleep',
    'study.error.loadInsights': 'Unable to load live planning insights.',
    'study.error.generatePlan': 'Unable to generate daily plan right now.',
    'study.error.updateTask': 'Unable to update task status.',
    'study.error.updateRecommendation': 'Unable to update recommendation right now.',
    'study.error.deleteRecommendation': 'Unable to delete recommendation right now.',
    'study.error.updateReview': 'Unable to update spaced review right now.',
    'study.error.updateMistake': 'Unable to update mistake card.',
    'study.error.minutesRange': 'Study minutes must be between 1 and 720.',
    'study.error.recordMinutes': 'Unable to record manual study minutes.',
    'study.recordedMinutes': 'Recorded {minutes} minutes in {subject}. +{xp} XP',
  },
  ta: {
    'app.student': 'மாணவர்',
    'app.level': 'நிலை {level}',
    'app.logout': 'வெளியேறு',
    'app.roleTooltip': 'பங்கு: {role}',
    'app.selectLanguage': 'மொழியை தேர்வு செய்யவும்',

    'nav.home': 'முகப்பு',
    'nav.ncertBooks': 'NCERT புத்தகங்கள்',
    'nav.achievements': 'சாதனைகள்',
    'nav.studyPlan': 'படிப்பு திட்டம்',
    'nav.learnSessions': 'கற்றல் அமர்வுகள்',
    'nav.notebookStudio': 'நோட்புக் ஸ்டூடியோ',
    'nav.resources': 'வளங்கள்',
    'nav.library': 'நூலகம்',
    'nav.notifications': 'அறிவிப்புகள்',
    'nav.support': 'உதவி',
    'nav.profile': 'சுயவிவரம்',

    'greeting.morning': 'காலை வணக்கம்',
    'greeting.afternoon': 'மதிய வணக்கம்',
    'greeting.evening': 'மாலை வணக்கம்',

    'home.updated': 'முகப்பு வெற்றிகரமாக புதுப்பிக்கப்பட்டது.',
    'home.liveRefreshFailed': 'நேரடி முகப்பு தரவை புதுப்பிக்க முடியவில்லை. உள்ளூர் மதிப்புகள் காட்டப்படுகின்றன.',
    'home.retry': 'மீண்டும் முயற்சி',
    'home.streakMessage': 'நீங்கள் {days} நாள் தொடரில் உள்ளீர்கள். இன்று உங்கள் முன்னேற்றத்தை தொடர்ந்து வைத்திருங்கள்.',
    'home.startStreak': 'இப்போது ஒரு கவனமான அமர்வை தொடங்கி உங்கள் தொடரை ஆரம்பிக்கவும்.',
    'home.levelXpBadge': 'நிலை {level} • {xp} XP',
    'home.streakChip': '{days} நாள் தொடர்',

    'home.xpToday': 'இன்றைய XP',
    'home.activeDays': 'செயலில் இருந்த நாட்கள்',
    'home.avgFocus': 'சராசரி கவனம்',
    'home.focus': 'கவனம்',
    'home.badges': 'பதக்கங்கள்',

    'home.dailyTarget': 'தினசரி இலக்கு',
    'home.goalHours': '{hours}மணி இலக்கு',
    'home.studiedToday': 'இன்று படித்தது',
    'home.hoursRemaining': '{hours}மணி மீதம்',
    'home.lessons': 'பாடங்கள்',
    'home.quizzes': 'வினாடி வினாக்கள்',

    'home.subjects': 'பாடப்பிரிவுகள்',
    'home.learn': 'கற்பது',
    'home.quiz': 'வினாடி வினா',
    'home.quickReferences': 'விரைவு குறிப்புகள்',
    'home.subject.physics.label': 'இயற்பியல்',
    'home.subject.physics.description': 'இயக்கவியல், வெப்பவியல், ஒளியியல், நவீன இயற்பியல்',
    'home.subject.chemistry.label': 'வேதியியல்',
    'home.subject.chemistry.description': 'கரிம, அகரிம, இயற்பு வேதியியல்',
    'home.subject.biology.label': 'உயிரியல்',
    'home.subject.biology.description': 'தாவரவியல், விலங்கியல், மரபியல், சூழலியல்',

    'home.xpToLevel': 'நிலை {level}க்கு இன்னும் {xp} XP',
    'home.badgesEarned': '{count} பதக்கங்கள் பெற்றது',
    'home.totalXp': 'மொத்தம் {xp} XP',

    'home.week': 'வாரம்',
    'home.month': 'மாதம்',
    'home.year': 'ஆண்டு',
    'home.previousPeriod': 'முந்தைய காலம்',
    'home.nextPeriod': 'அடுத்த காலம்',
    'home.dayNumber': 'நாள் {day}',
    'home.activeCount': '{count} செயலில்',
    'home.loadingActivity': '{view} செயல்பாடு ஏற்றப்படுகிறது...',

    'home.nextBestActions': 'அடுத்த சிறந்த செயல்கள்',
    'home.personalizedToday': 'இன்றைக்கான தனிப்பயன்',
    'home.open': 'திற',
    'home.personalizingActions': 'செயல்கள் தனிப்பயனாக்கப்படுகிறது...',

    'home.fallback.continueLearning.title': 'கற்றலை தொடருங்கள்',
    'home.fallback.continueLearning.description': 'உங்கள் சமீபத்திய அத்தியாயத்தை ஒரே சொடுக்கில் தொடருங்கள்.',
    'home.fallback.continueLearning.cta': 'அத்தியாயத்தை தொடருங்கள்',
    'home.fallback.smartRevision.title': 'சுறுசுறுப்பு மறுபார்வை',
    'home.fallback.smartRevision.description': 'தொடர்ச்சியை மேம்படுத்த குறுகிய பலவீனப் பகுதி வினாடி வினா எடுங்கள்.',
    'home.fallback.smartRevision.cta': '15 நிமிடம் மறுபார்வை',
    'home.fallback.planAhead.title': 'முன்கூட்டியே திட்டமிடுங்கள்',
    'home.fallback.planAhead.description': 'அடுத்த படிப்பு கட்டத்தை அமைத்து உங்கள் தொடரை பாதுகாப்பாக வைத்திருங்கள்.',
    'home.fallback.planAhead.cta': 'படிப்பு திட்டத்தை திற',

    'home.error.liveData': 'நேரடி முகப்பு தரவை ஏற்ற முடியவில்லை.',
    'home.error.nextActions': 'அடுத்த செயல்களை தனிப்பயனாக்க முடியவில்லை.',
    'home.error.heatmap': 'இந்த காலத்தின் செயல்பாட்டு வரைபடத்தை ஏற்ற முடியவில்லை.',

    'books.title': 'NCERT புத்தகங்கள்',
    'books.subtitle': 'NEET தயாரிப்பின் அடித்தளமான NCERT புத்தகங்களை நேரடியாக படிக்கவும்',
    'books.allSubjects': 'அனைத்து பாடங்களும்',
    'books.classSubject': 'வகுப்பு {classLevel} — {subject}',
    'books.chapterCount': '{count} அத்தியாயங்கள்',

    'ach.title': 'சாதனைகள்',
    'ach.refreshed': 'சாதனைகள் வெற்றிகரமாக புதுப்பிக்கப்பட்டது.',
    'ach.loadError': 'தற்போது சாதனைகளை ஏற்ற முடியவில்லை.',
    'ach.totalXp': 'மொத்த XP',
    'ach.levelLabel': 'நிலை',
    'ach.currentStreak': 'தற்போதைய தொடர்',
    'ach.badgesEarned': 'பெற்ற பதக்கங்கள்',
    'ach.xpToNext': 'அடுத்த நிலைக்கு {xp} XP',
    'ach.bestStreak': 'அதிகபட்ச தொடர்: {days} நாட்கள்',
    'ach.badges': 'பதக்கங்கள்',
    'ach.earned': '{date} அன்று பெற்றது',

    'study.title': 'படிப்பு திட்டம்',
    'study.daysUntilNeet': 'NEET {year} வரை உள்ள நாட்கள்',
    'study.stayFocused': 'கவனமாக இருங்கள், தொடர்ந்து செயல்படுங்கள்!',
    'study.todayProgress': 'இன்றைய முன்னேற்றம்',
    'study.studyTime': 'படிப்பு நேரம்',
    'study.adaptivePlan': 'தகவமைக்கப்பட்ட தினசரி திட்டம்',
    'study.refresh': 'புதுப்பி',
    'study.generatePlan': 'திட்டம் உருவாக்கு',
    'study.loadingPlanner': 'திட்டம் ஏற்றப்படுகிறது',
    'study.tasksCount': '{count} பணிகள்',
    'study.minutesPlanned': '{minutes} நிமிடம் திட்டமிடப்பட்டது',
    'study.completedCount': '{count} முடிந்தது',
    'study.pendingCount': '{count} நிலுவை',
    'study.adherence': '{percent}% பின்பற்றல்',
    'study.generalRevision': 'பொது மறுபார்வை',
    'study.allSubjects': 'அனைத்து பாடங்களும்',
    'study.minutes': 'நிமிடங்கள்',
    'study.priority': 'முன்னுரிமை {score}',
    'study.startMiniSet': 'மினி-செட் தொடங்கு',
    'study.startStamina': 'ஸ்டாமினா தொடங்கு',
    'study.done': 'முடிந்தது',
    'study.skip': 'தவிர்',
    'study.noPlannerTasks': 'இன்றைக்கு திட்டப் பணிகள் இல்லை. திட்டம் உருவாக்கு என்பதைக் கிளிக் செய்து உருவாக்கவும்.',
    'study.topRiskTopics': 'அதிக ஆபத்து தலைப்புகள்',
    'study.loadingRisks': 'ஆபத்துகள் ஏற்றப்படுகிறது',
    'study.noRiskTopics': 'இன்னும் ஆபத்து தலைப்புகள் இல்லை.',
    'study.calibrationWeekly': 'அளவுத்திருத்தம் & வார சுருக்கம்',
    'study.confidenceGap': 'நம்பிக்கை இடைவெளி',
    'study.confidentWrong': 'நம்பிக்கையுடன் தவறு',
    'study.retention': 'நினைவில் வைத்தல்',
    'study.accuracy': 'துல்லியம்',
    'study.speed': 'வேகம்',
    'study.spacedQueue': 'இடைவெளி மறுபார்வை வரிசை',
    'study.loadingQueue': 'வரிசை ஏற்றப்படுகிறது',
    'study.noDueRevisions': 'அடுத்த 48 மணிநேரத்தில் நிலுவை மறுபார்வைகள் இல்லை.',
    'study.due': 'நிலுவை {date}',
    'study.streak': 'தொடர் {count}',
    'study.correct': 'சரி',
    'study.partial': 'பகுதியாக',
    'study.incorrect': 'தவறு',
    'study.errorNotebook': 'பிழை குறிப்பேடு',
    'study.loadingMistakes': 'பிழைகள் ஏற்றப்படுகிறது',
    'study.generalConcept': 'பொது கருத்து',
    'study.repeatedTimes': '{count} முறை மீண்டும்',
    'study.markResolved': 'தீர்ந்ததாக குறி',
    'study.noMistakeCards': 'தற்போது செயலில் உள்ள பிழை அட்டைகள் இல்லை.',
    'study.thisWeek': 'இந்த வாரம் ({days} நாள் தொடர்)',
    'study.heatmapNote': 'ஹீட்மாப் /api/progress/daily இலிருந்து நேரடி தரவை உள்ளூர் மாற்றுடன் பயன்படுத்துகிறது.',
    'study.logMinutes': 'படிப்பு நிமிடங்களை பதிவு செய்',
    'study.minutesLabel': 'நிமிடங்கள்',
    'study.recordMinutes': 'நிமிடங்கள் பதிவு செய்',
    'study.readinessHabits': 'தயார்நிலை & பழக்கங்கள்',
    'study.noReadiness': 'தயார்நிலை snapshot இல்லை. ஒன்று உருவாக வினாடி வினா மற்றும் மறுபார்வையை தொடரவும்.',
    'study.unknownRisk': 'தெரியாத அபாயம்',
    'study.snapshot': 'snapshot {date}',
    'study.projectedScore': 'எதிர்பார்க்கும் மதிப்பெண்',
    'study.coverage': 'கவரேஜ்',
    'study.consistency': 'தொடர்ச்சி',
    'study.focusAvg': '7 நாள் கவனம் சராசரி: {minutes}நி/நாள்',
    'study.sessionsPerDay': 'ஒருநாள் அமர்வுகள்',
    'study.interruptionsPerDay': 'ஒருநாள் இடையூறுகள்',
    'study.mastery': 'தேர்ச்சி',
    'study.confidence': 'நம்பிக்கை',
    'study.masterySnapshot': 'தேர்ச்சி snapshot',
    'study.loadingMastery': 'தேர்ச்சி ஏற்றப்படுகிறது',
    'study.noMastery': 'இன்னும் தேர்ச்சி வரிசைகள் இல்லை. இதை நிரப்ப recall மற்றும் quiz முடிக்கவும்.',
    'study.activeRecommendations': 'செயலில் உள்ள பரிந்துரைகள்',
    'study.loadingRecommendations': 'பரிந்துரைகள் ஏற்றப்படுகிறது',
    'study.accept': 'ஏற்க',
    'study.dismiss': 'நிராகரி',
    'study.delete': 'நீக்கு',
    'study.noRecommendations': 'தற்போது செயலில் உள்ள பரிந்துரைகள் இல்லை. புதுப்பிக்க ஒரு திட்டம் உருவாக்கவும்.',
    'study.recommendationNote': 'பரிந்துரைகள் உங்கள் திட்டம், பலவீன தலைப்புகள், சமீபக் கற்றல் சிக்னல்களிலிருந்து தனிப்பயனாக்கப்படுகின்றன.',
    'study.suggestedRoutine': 'பரிந்துரைக்கப்பட்ட தினசரி நடைமுறை',
    'study.routine.slot1': 'இயற்பியல் — கோட்பாடு + NCERT வாசிப்பு',
    'study.routine.slot2': 'வேதியியல் — NCERT + MCQ பயிற்சி',
    'study.routine.slot3': 'உயிரியல் — NCERT + வரைபடங்கள்',
    'study.routine.slot4': 'மறுபார்வை — பலவீன தலைப்புகள்',
    'study.routine.slot5': 'APXMIND-ல் வினாடி வினா பயிற்சி',
    'study.routine.slot6': 'PYQ தீர்வு + பகுப்பாய்வு',
    'study.routine.slot7': 'தூக்கத்திற்கு முன் விரைவு மறுபார்வை',
    'study.error.loadInsights': 'நேரடி திட்டமிடல் உள்ளடக்கத்தை ஏற்ற முடியவில்லை.',
    'study.error.generatePlan': 'தற்போது தினசரி திட்டம் உருவாக்க முடியவில்லை.',
    'study.error.updateTask': 'பணி நிலையை புதுப்பிக்க முடியவில்லை.',
    'study.error.updateRecommendation': 'தற்போது பரிந்துரையை புதுப்பிக்க முடியவில்லை.',
    'study.error.deleteRecommendation': 'தற்போது பரிந்துரையை நீக்க முடியவில்லை.',
    'study.error.updateReview': 'இடைவெளி மறுபார்வையை புதுப்பிக்க முடியவில்லை.',
    'study.error.updateMistake': 'பிழை அட்டையை புதுப்பிக்க முடியவில்லை.',
    'study.error.minutesRange': 'படிப்பு நிமிடங்கள் 1 முதல் 720 வரை இருக்க வேண்டும்.',
    'study.error.recordMinutes': 'கையால் படிப்பு நிமிடங்களை பதிவு செய்ய முடியவில்லை.',
    'study.recordedMinutes': '{subject} இல் {minutes} நிமிடங்கள் பதிவு செய்யப்பட்டது. +{xp} XP',
  },
};

const TAMIL_BADGE_LOCALIZATION: Record<string, { name: string; description: string }> = {
  first_lesson: {
    name: 'முதல் படி',
    description: 'உங்கள் முதல் பாடத்தை நிறைவு செய்யுங்கள்.',
  },
  first_quiz: {
    name: 'க்விஸ் தொடக்கம்',
    description: 'உங்கள் முதல் வினாடி வினாவை முடிக்கவும்.',
  },
  perfect_quiz: {
    name: 'சரியான மதிப்பெண்',
    description: 'ஏதேனும் ஒரு வினாடி வினாவில் 100% பெறுங்கள்.',
  },
  streak_3: {
    name: '3 நாள் தொடர்',
    description: '3 நாட்கள் தொடர்ந்து படியுங்கள்.',
  },
  streak_7: {
    name: 'வார வீரர்',
    description: '7 நாட்கள் தொடர்ந்து படியுங்கள்.',
  },
  streak_30: {
    name: 'மாத மாஸ்டர்',
    description: '30 நாட்கள் தொடர்ந்து படியுங்கள்.',
  },
  quiz_master_10: {
    name: 'க்விஸ் மாஸ்டர்',
    description: '10 வினாடி வினாக்களை முடிக்கவும்.',
  },
  quiz_master_50: {
    name: 'க்விஸ் வீரர்',
    description: '50 வினாடி வினாக்களை முடிக்கவும்.',
  },
  bookworm: {
    name: 'புத்தக ஆர்வலர்',
    description: '10 புத்தகக்குறிகளை சேமிக்கவும்.',
  },
  note_taker: {
    name: 'குறிப்பெடுப்பவர்',
    description: '5 படிப்பு குறிப்புகளை உருவாக்கவும்.',
  },
  physicist: {
    name: 'இயற்பியல் நிபுணர்',
    description: 'இயற்பியல் க்விஸில் 90% க்கும் மேல் பெறுங்கள்.',
  },
  chemist: {
    name: 'வேதியியல் நிபுணர்',
    description: 'வேதியியல் க்விஸில் 90% க்கும் மேல் பெறுங்கள்.',
  },
  biologist: {
    name: 'உயிரியல் நிபுணர்',
    description: 'உயிரியல் க்விஸில் 90% க்கும் மேல் பெறுங்கள்.',
  },
  xp_500: {
    name: 'XP சேகரிப்பவர்',
    description: 'மொத்தம் 500 XP பெறுங்கள்.',
  },
  xp_5000: {
    name: 'XP களஞ்சியம்',
    description: 'மொத்தம் 5000 XP பெறுங்கள்.',
  },
  neet_ready: {
    name: 'NEET தயார்',
    description: 'NEET தயார்நிலையில் முக்கிய நிலையை அடையுங்கள்.',
  },
  early_bird: {
    name: 'அதிகாலை பறவை',
    description: 'காலை நேரத்தில் தொடர்ந்து படிப்பு செய்யுங்கள்.',
  },
  night_owl: {
    name: 'இரவு ஆந்தை',
    description: 'இரவு நேரங்களில் தொடர்ந்து படியுங்கள்.',
  },
  consistent_5: {
    name: 'தொடர்ச்சி சாம்பியன்',
    description: 'தினசரி படிப்பு இலக்கை 5 நாட்கள் தொடர்ந்து பூர்த்தி செய்யுங்கள்.',
  },
  all_subjects: {
    name: 'முழுமைப் படிப்பாளர்',
    description: 'ஒரே நாளில் மூன்று பாடங்களையும் படியுங்கள்.',
  },
  perfect_quiz_5: {
    name: 'சரியான ஐந்து',
    description: '5 க்விஸ்களில் 100% மதிப்பெண் பெறுங்கள்.',
  },
  perfect_quiz_10: {
    name: 'சரியான பத்து',
    description: '10 க்விஸ்களில் 100% மதிப்பெண் பெறுங்கள்.',
  },
  study_streak_30: {
    name: '30 நாள் போர்வீரர்',
    description: '30 நாட்கள் தொடர்ந்து படியுங்கள்.',
  },
  study_streak_60: {
    name: 'நிறுத்தமற',
    description: '60 நாட்கள் தொடர்ந்து படியுங்கள்.',
  },
  bio_master: {
    name: 'உயிரியல் மாஸ்டர்',
    description: 'உயிரியல் தலைப்புகளில் 90% க்கும் மேல் தேர்ச்சி பெறுங்கள்.',
  },
  chem_master: {
    name: 'வேதியியல் மாஸ்டர்',
    description: 'வேதியியல் தலைப்புகளில் 90% க்கும் மேல் தேர்ச்சி பெறுங்கள்.',
  },
  physics_master: {
    name: 'இயற்பியல் மாஸ்டர்',
    description: 'இயற்பியல் தலைப்புகளில் 90% க்கும் மேல் தேர்ச்சி பெறுங்கள்.',
  },
  speed_demon: {
    name: 'வேக சாம்பியன்',
    description: '1 மணிநேரத்தில் 100 கேள்விகளை தீர்க்கவும்.',
  },
  marathon: {
    name: 'மாரத்தான் படிப்பாளர்',
    description: 'ஒரே நாளில் 8+ மணிநேரம் படியுங்கள்.',
  },
};

const TAMIL_TOPIC_LOCALIZATION: Record<string, string> = {
  'Spaced review': 'இடைவெளி மறுபார்வை',
  'Error notebook': 'பிழை குறிப்பேடு',
  'Daily mixed mini-set': 'தினசரி கலப்பு மினி-செட்',
  'Due items': 'நிலுவை உருப்படிகள்',
  'Cross-subject': 'பல பாடங்கள்',
  'Timed section': 'நேர நிர்ணய பகுதி',
  'Weak area': 'பலவீன பகுதி',
};

const TAMIL_RECOMMENDATION_TITLE_PREFIXES: Record<string, string> = {
  'Revision: ': 'மறுபார்வை: ',
  'Mixed mini-set: ': 'கலப்பு மினி-செட்: ',
  'Stamina drill: ': 'ஸ்டாமினா பயிற்சி: ',
  'Concept build: ': 'கருத்து கட்டமைப்பு: ',
};

const TAMIL_RECOMMENDATION_REASONS: Record<string, string> = {
  'Due now in your spaced revision queue.': 'உங்கள் இடைவெளி மறுபார்வை வரிசையில் இது உடனே நிலுவையில் உள்ளது.',
  'Interleaved mixed practice to improve transfer.': 'பாடமாற்ற திறனை மேம்படுத்த கலப்பு இடைநுழைவு பயிற்சி.',
  'Timed practice to improve speed consistency.': 'வேகத் தொடர்ச்சியை உயர்த்த நேர நிர்ணய பயிற்சி.',
  'High-priority weak topic based on recent mastery.': 'சமீபத் தேர்ச்சியை அடிப்படையாகக் கொண்ட உயர் முன்னுரிமை பலவீன தலைப்பு.',
  'Personalized topic reinforcement.': 'தனிப்பயனாக்கப்பட்ட தலைப்பு வலுப்படுத்தல்.',
};

const TAMIL_RECOMMENDATION_TYPES: Record<string, string> = {
  daily_plan_task: 'தினசரி திட்ட பணி',
  revision: 'மறுபார்வை',
  lesson: 'பாடம்',
  quiz: 'க்விஸ்',
  routine: 'நடைமுறை',
  mini_set: 'மினி-செட்',
  stamina: 'ஸ்டாமினா',
  new_learning: 'புதிய கற்றல்',
};

const TAMIL_TASK_TYPES: Record<string, string> = {
  revision: 'மறுபார்வை',
  mini_set: 'மினி-செட்',
  stamina: 'ஸ்டாமினா',
  new_learning: 'புதிய கற்றல்',
  daily_plan_task: 'தினசரி திட்ட பணி',
};

const TAMIL_TASK_STATUSES: Record<string, string> = {
  pending: 'நிலுவை',
  completed: 'முடிந்தது',
  skipped: 'தவிர்க்கப்பட்டது',
};

function humanizeIdentifier(value: string): string {
  return value.replace(/_/g, ' ').trim();
}

export function localizeBadgeMetadata(
  language: string | null | undefined,
  badgeId: string,
  fallbackName: string,
  fallbackDescription: string
): { name: string; description: string } {
  if (resolveUiLanguage(language) !== 'ta') {
    return { name: fallbackName, description: fallbackDescription };
  }

  const localized = TAMIL_BADGE_LOCALIZATION[badgeId];
  if (!localized) {
    return { name: fallbackName, description: fallbackDescription };
  }

  return localized;
}

export function localizeTopicLabel(
  language: string | null | undefined,
  topic: string | null | undefined
): string {
  if (!topic) {
    return '';
  }
  if (resolveUiLanguage(language) !== 'ta') {
    return topic;
  }
  return TAMIL_TOPIC_LOCALIZATION[topic] ?? topic;
}

export function localizeRecommendationTitle(
  language: string | null | undefined,
  title: string
): string {
  if (!title || resolveUiLanguage(language) !== 'ta') {
    return title;
  }

  for (const [prefix, translatedPrefix] of Object.entries(TAMIL_RECOMMENDATION_TITLE_PREFIXES)) {
    if (!title.startsWith(prefix)) {
      continue;
    }
    const suffix = title.slice(prefix.length).trim();
    const translatedSuffix = localizeTopicLabel(language, suffix) || suffix;
    return `${translatedPrefix}${translatedSuffix}`;
  }

  return title;
}

export function localizeRecommendationReason(
  language: string | null | undefined,
  reason: string
): string {
  if (!reason || resolveUiLanguage(language) !== 'ta') {
    return reason;
  }
  return TAMIL_RECOMMENDATION_REASONS[reason] ?? reason;
}

export function localizeRecommendationType(
  language: string | null | undefined,
  recType: string
): string {
  if (!recType) {
    return '';
  }
  if (resolveUiLanguage(language) === 'ta') {
    return TAMIL_RECOMMENDATION_TYPES[recType] ?? humanizeIdentifier(recType);
  }
  return humanizeIdentifier(recType);
}

export function localizePlannerTaskType(
  language: string | null | undefined,
  taskType: string
): string {
  if (!taskType) {
    return '';
  }
  if (resolveUiLanguage(language) === 'ta') {
    return TAMIL_TASK_TYPES[taskType] ?? humanizeIdentifier(taskType);
  }
  return humanizeIdentifier(taskType);
}

export function localizePlannerTaskStatus(
  language: string | null | undefined,
  status: string
): string {
  if (!status) {
    return '';
  }
  if (resolveUiLanguage(language) === 'ta') {
    return TAMIL_TASK_STATUSES[status] ?? status;
  }
  return status;
}

function applyTemplate(template: string, vars?: TemplateVars): string {
  if (!vars) {
    return template;
  }

  return template.replace(/\{(\w+)\}/g, (_match, key: string) => {
    if (Object.prototype.hasOwnProperty.call(vars, key)) {
      return String(vars[key]);
    }
    return `{${key}}`;
  });
}

export function resolveUiLanguage(language: string | null | undefined): UiLanguage {
  const normalized = normalizeLanguage(language);
  return normalized === 'ta' ? 'ta' : 'en';
}

export function uiLocale(language: string | null | undefined): string {
  return resolveUiLanguage(language) === 'ta' ? 'ta-IN' : 'en-US';
}

export function tUi(
  language: string | null | undefined,
  key: string,
  vars?: TemplateVars
): string {
  const uiLanguage = resolveUiLanguage(language);
  const template =
    UI_TRANSLATIONS[uiLanguage][key] ?? UI_TRANSLATIONS.en[key] ?? key;
  return applyTemplate(template, vars);
}

export function weekdayLabels(language: string | null | undefined): string[] {
  if (resolveUiLanguage(language) === 'ta') {
    return ['ஞா', 'தி', 'செ', 'பு', 'வி', 'வெ', 'ச'];
  }

  return ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
}
