// Icon fonts load assets at runtime; tests render a plain placeholder instead.
const { Text } = require("react-native");
const Icon = ({ name }) => require("react").createElement(Text, null, name);
Icon.loadFont = () => Promise.resolve();
module.exports = { __esModule: true, default: Icon, MaterialCommunityIcons: Icon };
