// Metro and Jest resolve image requires to an asset reference.
declare module "*.jpg" {
  const asset: number;
  export default asset;
}
