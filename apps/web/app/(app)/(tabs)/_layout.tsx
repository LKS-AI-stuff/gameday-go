import { TABS, tabIcon, tabScreenOptions } from "@gamedaygo/ui";
import { Tabs } from "expo-router";
import { useWindowDimensions } from "react-native";

// Bottom tabs, or a left navigation rail on wide windows (UI/UX §2.2).
export default function TabsLayout() {
  const { width } = useWindowDimensions();
  return (
    <Tabs screenOptions={tabScreenOptions(width >= 1024)}>
      {TABS.map((tab) => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{ title: tab.title, tabBarIcon: tabIcon(tab.icon) }}
        />
      ))}
    </Tabs>
  );
}
