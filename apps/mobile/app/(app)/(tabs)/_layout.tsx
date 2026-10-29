import { TABS, tabIcon, tabScreenOptions } from "@gamedaygo/ui";
import { Tabs } from "expo-router";

// Bottom tabs: Home, Schedule, Plan, My Game Days (UI/UX §2.2).
export default function TabsLayout() {
  return (
    <Tabs screenOptions={tabScreenOptions(false)}>
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
