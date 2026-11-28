import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Animated,
  Dimensions,
  PanResponder,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";

import sampleCardsData from "./src/sampleCards.json";
import {
  STORAGE_KEYS,
  fetchDiffCardsFromLan,
  normalizeLanBaseUrl,
  parsePrTarget,
  postDecisionsToGithubPr,
  recordSwipeDecision,
  summarizeDecisions,
} from "./src/cardUtils";

const SCREEN_WIDTH = Dimensions.get("window").width;
const SWIPE_THRESHOLD = SCREEN_WIDTH * 0.28;

export default function App() {
  const [lanIp, setLanIp] = useState("https://speccraftai.onrender.com");
  const [prTarget, setPrTarget] = useState("poorav007/SpeccraftAI#1");
  const [showSettings, setShowSettings] = useState(false);
  const [cardsPayload, setCardsPayload] = useState(sampleCardsData);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [decisions, setDecisions] = useState({});
  const [sourceMode, setSourceMode] = useState("Offline sample cards.json");
  const [statusMsg, setStatusMsg] = useState("");

  const pan = useRef(new Animated.ValueXY()).current;

  useEffect(() => {
    async function hydrateStorage() {
      try {
        const [savedUrl, savedDecisions] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEYS.LAN_URL),
          AsyncStorage.getItem(STORAGE_KEYS.DECISIONS),
        ]);
        if (savedUrl) setLanIp(savedUrl);
        if (savedDecisions) setDecisions(JSON.parse(savedDecisions));
      } catch {
        // Ignore storage read errors in fresh Expo Go sandboxes
      }
    }
    hydrateStorage();
  }, []);

  const cards = cardsPayload.cards || [];
  const activeCard = cards[currentIndex] || null;
  const stats = useMemo(() => summarizeDecisions(decisions), [decisions]);

  async function persistDecisions(nextMap) {
    setDecisions(nextMap);
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.DECISIONS, JSON.stringify(nextMap));
    } catch {
      // Safe fallback
    }
  }

  function completeCardSwipe(direction) {
    if (!activeCard) return;
    const toX = direction === "approved" ? SCREEN_WIDTH + 80 : -SCREEN_WIDTH - 80;
    Animated.timing(pan, {
      toValue: { x: toX, y: 0 },
      duration: 180,
      useNativeDriver: false,
    }).start(async () => {
      const nextMap = recordSwipeDecision(decisions, activeCard, direction);
      await persistDecisions(nextMap);
      pan.setValue({ x: 0, y: 0 });
      setCurrentIndex((i) => i + 1);
    });
  }

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => Boolean(activeCard),
        onMoveShouldSetPanResponder: (_, gesture) => Math.abs(gesture.dx) > 8,
        onPanResponderMove: Animated.event([null, { dx: pan.x }], {
          useNativeDriver: false,
        }),
        onPanResponderRelease: (_, gesture) => {
          if (gesture.dx > SWIPE_THRESHOLD || gesture.vx > 0.65) {
            completeCardSwipe("approved");
          } else if (gesture.dx < -SWIPE_THRESHOLD || gesture.vx < -0.65) {
            completeCardSwipe("blocked");
          } else {
            Animated.spring(pan, {
              toValue: { x: 0, y: 0 },
              friction: 6,
              useNativeDriver: false,
            }).start();
          }
        },
      }),
    [activeCard, decisions]
  );

  async function handleFetchFromLan() {
    const normalized = normalizeLanBaseUrl(lanIp);
    if (!normalized) {
      setStatusMsg("Enter a valid laptop LAN IP (e.g. 192.168.1.42:8000)");
      return;
    }
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.LAN_URL, lanIp);
    } catch {
      // Ignore storage error
    }

    setStatusMsg(`Connecting to ${normalized}...`);
    const sampleDiffInput = {
      summary: { total_changes: sampleCardsData.cards.length, breaking_changes: 2 },
      changes: sampleCardsData.cards.map((c) => {
        const [method = "get", path = "/"] = c.endpoint.split(" ");
        return {
          path,
          method: method.toLowerCase(),
          is_breaking: c.severity === "breaking",
          description: c.one_line_impact,
          old_value: c.before,
          new_value: c.after,
        };
      }),
    };

    const res = await fetchDiffCardsFromLan(lanIp, sampleDiffInput);
    if (res.ok && res.data?.cards) {
      setCardsPayload(res.data);
      setCurrentIndex(0);
      setSourceMode(`Live LAN (${normalized})`);
      setStatusMsg(`Loaded ${res.data.cards.length} card(s) via ${res.data.provider}`);
    } else {
      setCardsPayload(sampleCardsData);
      setSourceMode("Offline sample cards.json (fallback)");
      setStatusMsg(`LAN unreachable (${res.error}); using offline sample.`);
    }
  }

  async function handleResetSession() {
    setCurrentIndex(0);
    await persistDecisions({});
    setStatusMsg("Cleared review decisions.");
  }

  async function handlePostToGithubPr() {
    const parsed = parsePrTarget(prTarget);
    if (!parsed) {
      setStatusMsg("Enter PR target as owner/repo#number (e.g. poorav007/SpeccraftAI#12)");
      return;
    }
    setStatusMsg(`Posting review to ${parsed.owner}/${parsed.repo}#${parsed.prNumber}...`);
    const res = await postDecisionsToGithubPr(lanIp, {
      ...parsed,
      decisions,
    });
    if (res.ok && res.data?.posted) {
      setStatusMsg(`Posted PR comment: ${res.data.comment_url}`);
    } else if (res.ok) {
      setStatusMsg(`Generated PR review preview (${res.data?.reason || "token unset"}).`);
    } else {
      setStatusMsg(res.error);
    }
  }

  const cardRotate = pan.x.interpolate({
    inputRange: [-SCREEN_WIDTH / 2, 0, SCREEN_WIDTH / 2],
    outputRange: ["-7deg", "0deg", "7deg"],
    extrapolate: "clamp",
  });

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.root}>
        <StatusBar style="dark" />
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>SpecCraft Swipe Review</Text>
            <Text style={styles.subtitle}>{sourceMode}</Text>
          </View>
          <TouchableOpacity
            style={styles.settingsBtn}
            onPress={() => setShowSettings((v) => !v)}
          >
            <Text style={styles.settingsBtnText}>{showSettings ? "Hide Settings" : "Backend / PR"}</Text>
          </TouchableOpacity>
        </View>

        {showSettings && (
          <View style={styles.settingsBox}>
            <Text style={styles.label}>SpecCraft Backend URL (Cloud Render or Laptop LAN IP)</Text>
            <TextInput
              style={styles.input}
              value={lanIp}
              onChangeText={setLanIp}
              placeholder="https://speccraftai.onrender.com or 192.168.1.42:8000"
              autoCapitalize="none"
              autoCorrect={false}
            />
            <Text style={styles.label}>GitHub PR Target (owner/repo#number)</Text>
            <TextInput
              style={styles.input}
              value={prTarget}
              onChangeText={setPrTarget}
              placeholder="poorav007/SpeccraftAI#12"
              autoCapitalize="none"
              autoCorrect={false}
            />
            <View style={styles.row}>
              <TouchableOpacity style={styles.primaryBtn} onPress={handleFetchFromLan}>
                <Text style={styles.btnTextWhite}>Fetch Live Diff</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.secondaryBtn}
                onPress={() => {
                  setCardsPayload(sampleCardsData);
                  setCurrentIndex(0);
                  setSourceMode("Offline sample cards.json");
                  setStatusMsg("Switched to bundled offline cards.json.");
                }}
              >
                <Text style={styles.btnTextDark}>Offline Sample</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {Boolean(statusMsg) && <Text style={styles.status}>{statusMsg}</Text>}

        <View style={styles.counterRow}>
          <Text style={[styles.counterPill, styles.approvePill]}>Approved: {stats.approved}</Text>
          <Text style={[styles.counterPill, styles.blockPill]}>Blocked: {stats.blocked}</Text>
          <Text style={styles.counterPill}>
            Card {Math.min(currentIndex + 1, cards.length)} / {cards.length}
          </Text>
        </View>

        {activeCard ? (
          <View style={styles.deckArea}>
            <Animated.View
              {...panResponder.panHandlers}
              style={[
                styles.card,
                { transform: [{ translateX: pan.x }, { rotate: cardRotate }] },
              ]}
            >
              <View style={styles.cardTop}>
                <Text style={styles.endpoint}>{activeCard.endpoint}</Text>
                <View
                  style={[
                    styles.sevBadge,
                    activeCard.severity === "breaking" ? styles.sevBreaking : styles.sevSafe,
                  ]}
                >
                  <Text style={styles.sevText}>
                    {activeCard.severity === "breaking" ? "BREAKING" : "NON-BREAKING"}
                  </Text>
                </View>
              </View>
              <Text style={styles.impact}>{activeCard.one_line_impact}</Text>
              <View style={styles.diffBox}>
                <Text style={styles.diffLabel}>Before:</Text>
                <Text style={styles.diffCode}>{activeCard.before}</Text>
                <Text style={[styles.diffLabel, { marginTop: 8 }]}>After:</Text>
                <Text style={styles.diffCode}>{activeCard.after}</Text>
              </View>
              <Text style={styles.swipeHint}>Swipe Left to Block · Swipe Right to Approve</Text>
            </Animated.View>

            <View style={styles.actionRow}>
              <TouchableOpacity
                style={[styles.actionBtn, styles.blockBtn]}
                onPress={() => completeCardSwipe("blocked")}
              >
                <Text style={styles.btnTextWhite}>✕ Block</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionBtn, styles.approveBtn]}
                onPress={() => completeCardSwipe("approved")}
              >
                <Text style={styles.btnTextWhite}>✓ Approve</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <ScrollView style={styles.summaryList}>
            <Text style={styles.doneTitle}>Review Complete</Text>
            <Text style={styles.doneSub}>
              Saved {stats.total} persisted decision(s) ({stats.approved} approved, {stats.blocked} blocked).
            </Text>
            {Object.values(decisions).map((d) => (
              <View key={d.endpoint} style={styles.decisionRow}>
                <Text style={styles.decisionEp}>{d.endpoint}</Text>
                <Text
                  style={[
                    styles.decisionTag,
                    d.decision === "approved" ? styles.approvePill : styles.blockPill,
                  ]}
                >
                  {d.decision.toUpperCase()}
                </Text>
              </View>
            ))}
            <TouchableOpacity style={styles.primaryBtn} onPress={handlePostToGithubPr}>
              <Text style={styles.btnTextWhite}>Post Decisions to GitHub PR</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.resetBtn} onPress={handleResetSession}>
              <Text style={styles.btnTextWhite}>Restart Review</Text>
            </TouchableOpacity>
          </ScrollView>
        )}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#f8fafc", paddingHorizontal: 16 },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 12 },
  title: { fontSize: 19, fontWeight: "700", color: "#0f172a" },
  subtitle: { fontSize: 12, color: "#64748b", marginTop: 2 },
  settingsBtn: { backgroundColor: "#e2e8f0", paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  settingsBtnText: { fontSize: 12, fontWeight: "600", color: "#0f172a" },
  settingsBox: { backgroundColor: "#fff", padding: 12, borderRadius: 10, borderWidth: 1, borderColor: "#e2e8f0", marginBottom: 10 },
  label: { fontSize: 11, color: "#475569", marginBottom: 6, fontWeight: "600" },
  input: { borderWidth: 1, borderColor: "#cbd5e1", borderRadius: 8, padding: 10, fontSize: 16, marginBottom: 10, color: "#0f172a" },
  row: { flexDirection: "row", gap: 8 },
  primaryBtn: { flex: 1, backgroundColor: "#0d6efd", paddingVertical: 10, borderRadius: 8, alignItems: "center" },
  secondaryBtn: { flex: 1, backgroundColor: "#e2e8f0", paddingVertical: 10, borderRadius: 8, alignItems: "center" },
  status: { fontSize: 12, color: "#2563eb", marginBottom: 8 },
  counterRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 12 },
  counterPill: { fontSize: 12, fontWeight: "600", color: "#334155", backgroundColor: "#e2e8f0", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  approvePill: { backgroundColor: "#dcfce7", color: "#166534" },
  blockPill: { backgroundColor: "#fee2e2", color: "#991b1b" },
  deckArea: { flex: 1, justifyContent: "center" },
  card: { backgroundColor: "#ffffff", borderRadius: 16, padding: 20, borderWidth: 1, borderColor: "#e2e8f0", shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 12, elevation: 3 },
  cardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12, gap: 8 },
  endpoint: { fontSize: 16, fontWeight: "700", color: "#0f172a", flexShrink: 1 },
  sevBadge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  sevBreaking: { backgroundColor: "#dc3545" },
  sevSafe: { backgroundColor: "#198754" },
  sevText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  impact: { fontSize: 15, color: "#334155", lineHeight: 22, marginBottom: 14 },
  diffBox: { backgroundColor: "#f8fafc", padding: 12, borderRadius: 10, borderWidth: 1, borderColor: "#e2e8f0" },
  diffLabel: { fontSize: 11, fontWeight: "700", color: "#64748b" },
  diffCode: { fontSize: 12, color: "#0f172a", marginTop: 2 },
  swipeHint: { textAlign: "center", fontSize: 11, color: "#94a3b8", marginTop: 14 },
  actionRow: { flexDirection: "row", gap: 12, marginTop: 20 },
  actionBtn: { flex: 1, paddingVertical: 14, borderRadius: 12, alignItems: "center" },
  blockBtn: { backgroundColor: "#dc3545" },
  approveBtn: { backgroundColor: "#198754" },
  btnTextWhite: { color: "#fff", fontWeight: "700", fontSize: 15 },
  btnTextDark: { color: "#0f172a", fontWeight: "700", fontSize: 13 },
  summaryList: { flex: 1, paddingTop: 12 },
  doneTitle: { fontSize: 20, fontWeight: "700", color: "#0f172a" },
  doneSub: { fontSize: 13, color: "#475569", marginBottom: 14, marginTop: 4 },
  decisionRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", backgroundColor: "#fff", padding: 12, borderRadius: 10, borderWidth: 1, borderColor: "#e2e8f0", marginBottom: 8 },
  decisionEp: { fontWeight: "600", color: "#0f172a", flexShrink: 1 },
  decisionTag: { fontSize: 11, fontWeight: "700", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  resetBtn: { backgroundColor: "#0f172a", paddingVertical: 14, borderRadius: 10, alignItems: "center", marginTop: 12 },
});

